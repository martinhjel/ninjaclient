# NinjaClient
NinjaClient is a Python library designed to simplify accessing and querying data from the [Renewables Ninja API](https://www.renewables.ninja/). It provides an easy-to-use interface for fetching detailed renewable energy data, including solar and wind energy generation estimates. Whether you're conducting research, analyzing energy markets, or building renewable energy forecasting models, NinjaClient offers the tools you need to get the data quickly and efficiently.

## Features
- Fetch solar generation data based on location, time, and panel specifications. 
- Retrieve wind energy data by specifying turbine details, location, and time range.
- Handle API rate limiting gracefully with built-in waiting and retry mechanisms.
- Simplify the process of working with renewable energy data for analysis and modeling.

## Installation
To install NinjaClient, you need Python 3.9 or later. It's recommended to install NinjaClient within a virtual environment. Run the following command to install:

```bash
pip install ninjaclient
```

## Quick Start
Here's a quick example to get you started with NinjaClient:

```python
from ninjaclient import NinjaClient

# Initialize the client with your API token
ninja_client  = NinjaClient(web_token='YOUR_API_TOKEN_HERE')

df_countries = ninja_client.get_countries()
limits = ninja_client.get_limits()

# Fetch wind generation data
df_wind, wind_meta = ninja_client.get_wind_dataframe(
    lat=56,
    lon=6,
    date_from="2000-01-01",
    date_to="2001-12-31"
)

# Fetch solar generation data
df_solar, solar_meta = ninja_client.get_solar_dataframe(
    lat=56,
    lon=6,
    date_from="2000-01-01",
    date_to="2001-12-31"
)
```

The API Token you can find under your Renewable Ninja [profile](https://www.renewables.ninja/profile). 

## Documentation
For detailed documentation on all available methods and their parameters, please refer to the Renewables Ninja API [documentation](https://www.renewables.ninja/documentation).

## Contributing
Contributions to NinjaClient are welcome! If you have suggestions for improvements or bug fixes, please open an issue or submit a pull request.

## License
NinjaClient is released under the MIT License. See the LICENSE file for more details.

## Acknowledgments
Thanks to the Renewables Ninja project for providing the API that this client library interacts with.
This project is not officially associated with the Renewables Ninja project.