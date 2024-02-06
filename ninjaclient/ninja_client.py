import json
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from io import StringIO


class NinjaClient:
    """
    A client for querying data from the Renewables Ninja API.

    :param web_token: A valid API token for authenticating requests.
    :type web_token: str

    The client handles querying wind and solar data, managing API rate limits, and parsing the responses into pandas DataFrames.
    """

    BASE_URI = "https://www.renewables.ninja/api/"
    PV_URI = BASE_URI + "data/pv"
    WIND_URI = BASE_URI + "data/wind"
    COUNTRIES_URI = BASE_URI + "countries"
    LIMITS_URI = BASE_URI + "limits"

    def __init__(self, web_token: str | None):
        """
        Initializes the NinjaClient with the provided API token.
        """
        self.headers = {"Authorization": f"Token {web_token}"}
        self.last_query_time = pd.Timestamp("2020-01-01T00:00:00")
        if web_token:
            self.burst_time_limit, self.max_queries_per_hour = self._compute_limits()
        else:
            self.burst_time_limit, self.max_queries_per_hour = pd.Timedelta("0 days 00:00:01"), 50

    def _compute_limits(self) -> (pd.Timedelta, int):
        """
        Computes the API's burst and sustained request limits based on the API's limit response.

        :return: A tuple containing the burst time limit as a pandas Timedelta and the maximum queries per hour as an integer.
        :rtype: tuple
        """
        limits = self.get_limits()
        freq, time_unit = limits["burst"].split("/")
        burst_time = pd.Timedelta(f"{1/int(freq)} {time_unit}")

        max_per_hour = int(limits["sustained"].split("/")[0])

        return burst_time, max_per_hour

    def wait_for_burst(self) -> None:
        """
        Waits until the next burst of requests is allowed, based on the last query time and burst limit.
        """
        while pd.Timestamp.now() - self.last_query_time < self.burst_time_limit:
            time.sleep(1)

    def _multiple_dates_queries(self, uri: str, args: dict) -> (pd.DataFrame, list):
        """
        Handles queries spanning multiple periods by splitting them into smaller, allowable queries.

        :param uri: The API endpoint URI.
        :type uri: str
        :param args: The query parameters.
        :type args: dict
        :return: A tuple containing a pandas DataFrame of the combined query results and a list of metadata from each query.
        :rtype: tuple
        """
        date_froms, date_tos = self._get_periods(date_from=args["date_from"], date_to=args["date_to"])
        df = pd.DataFrame()
        metadata = []
        for date_from, date_to in zip(date_froms, date_tos):
            args["date_from"] = date_from
            args["date_to"] = date_to
            df_i, meta = self._query(uri, args)
            df = pd.concat((df, df_i), axis=0)
            metadata.append(meta)

        return df, metadata

    def _query(self, uri: str, args: dict) -> (pd.DataFrame, dict):
        """
        Performs a single API query and handles the response.

        :param uri: The API endpoint URI.
        :type uri: str
        :param args: The query parameters.
        :type args: dict
        :return: A tuple containing a pandas DataFrame of the query results and the query's metadata.
        :rtype: tuple
        :raises Exception: If the API request fails.
        """
        self.wait_for_burst()
        res = requests.get(uri, params=args, headers=self.headers)

        if res.status_code == 429:
            print(res.text)
            available_in_seconds = int(res.text.split(" ")[-2])
            time.sleep(available_in_seconds)
            res = requests.get(uri, params=args, headers=self.headers)

        try:
            res.raise_for_status()
        except Exception as e:
            print(res.text)
            raise e

        self.last_query_time = pd.Timestamp.now()
        parsed_response = res.json()
        df = pd.read_json(StringIO(json.dumps(parsed_response["data"])), orient="index")
        metadata = parsed_response["metadata"]

        return df, metadata

    def _get_periods(self, date_from: str, date_to: str):
        """
        Splits the query period into one-year periods if it spans more than one year.

        :param date_from: The start date of the period (YYYY-MM-DD).
        :type date_from: str
        :param date_to: The end date of the period (YYYY-MM-DD).
        :type date_to: str
        :return: Two lists containing the start and end dates of each sub-period.
        :rtype: tuple
        """
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

        date_tos = []
        date_froms = [date_from]
        for y_delta in range((date_to.year - date_from.year)):
            date_tos.append(date(year=date_froms[-1].year, month=12, day=31))
            date_froms.append(date_tos[-1] + timedelta(days=1))

        date_tos.append(date_to)

        return ([d.strftime("%Y-%m-%d") for d in date_froms], [d.strftime("%Y-%m-%d") for d in date_tos])

    def get_wind_dataframe(
        self,
        lat,
        lon,
        date_from,
        date_to,
        dataset="merra2",
        capacity=1.0,
        height=100,
        turbine="Vestas V80 2000",
        interpolate=False,
    ):
        """
        Retrieves wind data for a specified location and time period.

        :param lat: Latitude of the location.
        :type lat: float
        :param lon: Longitude of the location.
        :type lon: float
        :param date_from: Start date for the data retrieval (YYYY-MM-DD).
        :type date_from: str
        :param date_to: End date for the data retrieval (YYYY-MM-DD).
        :type date_to: str
        :param dataset: The dataset to use. Default is "merra2".
        :type dataset: str, optional
        :param capacity: Installed capacity in kW. Default is 1.0.
        :type capacity: float, optional
        :param height: Hub height of the turbine in meters. Default is 100.
        :type height: int, optional
        :param turbine: Model of the wind turbine. Default is "Vestas V80 2000".
        :type turbine: str, optional
        :param interpolate: Whether to interpolate the data. Default is False.
        :type interpolate: bool, optional
        :return: A tuple containing a pandas DataFrame of the wind data and a list of metadata for each query.
        :rtype: tuple
        """
        args = {
            "lat": lat,
            "lon": lon,
            "date_from": date_from,
            "date_to": date_to,
            "dataset": dataset,
            "capacity": capacity,
            "height": height,
            "turbine": turbine,
            "interpolate": interpolate,
            "format": "json",
        }

        return self._multiple_dates_queries(NinjaClient.WIND_URI, args)

    def get_solar_dataframe(
        self,
        lat: float,
        lon: float,
        date_from,
        date_to,
        dataset="merra2",
        capacity: float = 1.0,
        system_loss: float = 0.1,
        tracking=0,
        tilt=35,
        azim=180,
        interpolate=False,
    ):
        """
        Retrieves solar data for a specified location and time period.

        :param lat: Latitude of the location.
        :type lat: float
        :param lon: Longitude of the location.
        :type lon: float
        :param date_from: Start date for the data retrieval (YYYY-MM-DD).
        :type date_from: str
        :param date_to: End date for the data retrieval (YYYY-MM-DD).
        :type date_to: str
        :param dataset: The dataset to use. Default is "merra2".
        :type dataset: str, optional
        :param capacity: Installed capacity in kW. Default is 1.0.
        :type capacity: float, optional
        :param system_loss: System losses in percentage. Default is 0.1.
        :type system_loss: float, optional
        :param tracking: Tracking type (0 for fixed, 1 for single-axis). Default is 0.
        :type tracking: int, optional
        :param tilt: Tilt angle of the solar panel. Default is 35.
        :type tilt: int, optional
        :param azim: Azimuth angle of the solar panel. Default is 180.
        :type azim: int, optional
        :param interpolate: Whether to interpolate the data. Default is False.
        :type interpolate: bool, optional
        :return: A tuple containing a pandas DataFrame of the solar data and a list of metadata for each query.
        :rtype: tuple
        """
        args = {
            "lat": lat,
            "lon": lon,
            "date_from": date_from,
            "date_to": date_to,
            "dataset": dataset,
            "capacity": capacity,
            "system_loss": system_loss,
            "tracking": tracking,
            "tilt": tilt,
            "azim": azim,
            "interpolate": interpolate,
            "format": "json",
        }

        return self._multiple_dates_queries(NinjaClient.PV_URI, args)

    def get_countries(self) -> pd.DataFrame:
        """
        Retrieves a list of countries available in the Renewables Ninja API.

        :return: A pandas DataFrame containing the list of countries.
        :rtype: pandas.DataFrame
        """
        res = requests.get(NinjaClient.COUNTRIES_URI, headers=self.headers)
        return pd.DataFrame(res.json()["countries"])

    def get_limits(self) -> dict:
        """
        Fetches the current API usage limits.

        :return: A dictionary containing the API's burst and sustained limits.
        :rtype: dict
        """
        res = requests.get(NinjaClient.LIMITS_URI, headers=self.headers)
        return res.json()


if __name__ == "__main__":
    from configparser import ConfigParser

    config = ConfigParser()
    config.read("config.ini")

    ninja_client = NinjaClient(web_token=config["renewables_ninja"]["web_token"])

    df_countries = ninja_client.get_countries()
    limits = ninja_client.get_limits()

    df_wind, wind_meta = ninja_client.get_wind_dataframe(lat=6, lon=56, date_from="2000-01-01", date_to="2001-12-31")
    df_solar, solar_meta = ninja_client.get_solar_dataframe(lat=6, lon=56, date_from="2000-01-01", date_to="2001-12-31")
    