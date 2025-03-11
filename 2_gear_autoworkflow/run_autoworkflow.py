import os
import flywheel
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('main')

# import custom helper functions, need to first add path to system envrionment... 
#      do that using current directory inside jupyter notebooks, 
#      or __file__ attribute in script
try:
    absolute_path = os.path.abspath(__file__)
    sys.path.insert(0, Path(absolute_path).parts[0:-2])
except NameError:
    sys.path.insert(0, os.path.dirname(os.getcwd()))
from _helper_functions import gears

# set default permissions
os.umask(0o002);

# get flywheel client
fw = flywheel.Client('')


if __name__ == "__main__":
    
    # locate sessions generated within lookback window
    lookback = 7
    created_by = gears.get_x_days_ago(lookback).strftime('%Y-%m-%d')
    filtered_sessions=fw.sessions.find(f'created>{created_by}')

    #Loop through sessions and see which ones apply for the gear rule to kick off
    for session in filtered_sessions:
        sid = session.id

        log.info("checking workflow: %s/%s/%s",fw.get_project(fw.get_session(sid).parents["project"]).label, fw.get_session(sid).subject.label, fw.get_session(sid).label)

        try:
            gears.run_auto_gear(sid)
        except Exception as e:
            log.warning(e)
    