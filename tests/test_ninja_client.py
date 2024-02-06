import pandas as pd
import pytest
import requests_mock

from ninjaclient import NinjaClient  # Adjust the import path as necessary


@pytest.fixture
def ninja_client():
    """Fixture to create a NinjaClient instance with a mock web token."""
    client = NinjaClient(web_token=None)

    return client


def test_get_countries(ninja_client):
    with requests_mock.Mocker() as m:
        mock_response = {
            "countries": {
                "class": {0: "renewables_corrected_and_weather", 1: "renewables_corrected_and_weather"},
                "id": {0: "ES", 1: "AT"},
                "name": {0: "Spain", 1: "Austria"},
            }
        }

        m.get(NinjaClient.COUNTRIES_URI, json=mock_response)

        df_countries = ninja_client.get_countries()
        assert isinstance(df_countries, pd.DataFrame)
        assert len(df_countries) == 2
        assert df_countries.iloc[0]["name"] == "Spain"


def test_get_limits(ninja_client):
    with requests_mock.Mocker() as m:
        mock_response = {"sustained": "50/hour", "burst": "1/second"}
        m.get(NinjaClient.LIMITS_URI, json=mock_response)

        limits = ninja_client.get_limits()
        assert ninja_client.burst_time_limit == pd.Timedelta("0 days 00:00:01")
        assert ninja_client.max_queries_per_hour == 50
        assert limits == mock_response


@pytest.mark.parametrize(
    "date_from,date_to,expected",
    [
        ("2020-01-01", "2020-12-31", (["2020-01-01"], ["2020-12-31"])),
        ("2020-01-01", "2021-01-01", (["2020-01-01", "2021-01-01"], ["2020-12-31", "2021-01-01"])),
        (
            "2020-01-01",
            "2022-01-01",
            (
                ["2020-01-01", "2021-01-01", "2022-01-01"],
                ["2020-12-31", "2021-12-31", "2022-01-01"],
            ),
        ),
        (
            "2020-01-01",
            "2023-03-15",
            (
                ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"],
                ["2020-12-31", "2021-12-31", "2022-12-31", "2023-03-15"],
            ),
        ),
    ],
)
def test_get_periods(ninja_client, date_from, date_to, expected):
    result = ninja_client._get_periods(date_from, date_to)
    expected_froms, expected_tos = expected
    result_froms, result_tos = result

    assert result_froms == expected_froms
    assert result_tos == expected_tos


def test_get_wind_dataframe(ninja_client):
    with requests_mock.Mocker() as m:
        mock_response = {"data": {}, "metadata": {}}
        m.get(NinjaClient.WIND_URI, json=mock_response)

        df, metadata = ninja_client.get_wind_dataframe(
            lat=40.7128, lon=-74.0060, date_from="2020-01-01", date_to="2020-01-02"
        )
        assert isinstance(df, pd.DataFrame)
        assert isinstance(metadata, list)


def test_get_solar_dataframe(ninja_client):
    with requests_mock.Mocker() as m:
        mock_response = {"data": {}, "metadata": {}}
        m.get(NinjaClient.PV_URI, json=mock_response)

        df, metadata = ninja_client.get_solar_dataframe(
            lat=40.7128, lon=-74.0060, date_from="2021-01-01", date_to="2021-01-02"
        )
        assert isinstance(df, pd.DataFrame)
        assert isinstance(metadata, list)
