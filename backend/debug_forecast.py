import traceback
from models.rolling_forecast import RollingForecast
r = RollingForecast('rizer_data.db')
try:
    print(r.run('revenue', 6))
except Exception as e:
    print(traceback.format_exc())
