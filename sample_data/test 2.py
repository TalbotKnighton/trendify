
import trendify
import trendify.plotly_dashboard
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.DEBUG, # Minimum level of messages to log
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # Format of log messages
    filename='app.log', # File to write logs to
    filemode='w' # Mode to open the file ('w' for write, 'a' for append)
) 


collection = trendify.DataProductCollection.collect_from_all_jsons(
    Path(__file__).parent.joinpath('models'),
    recursive=True,
)
# print(collection)
# Create and run the dashboard with your collection
trendify.plotly_dashboard.run_plotly_dashboard(
    collection, 
    title="My Data Dashboard",
)