from datetime import datetime, timezone, timedelta
from game import expire_if_needed, process_location
from config import GAME_CONFIG


def test_expiry_without_new_gps():
    game = {'game_id':'x','player_name':'t','phase':'FIND_WAND_AND_BROOM','reached':[3],
            'deadline':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),
            'boosts':{}, 'message_queue':[], 'last_location':None}
    assert expire_if_needed(game)
    assert game['phase']=='GAME_OVER'
    assert not expire_if_needed(game)


def test_premature_checkpoints_do_not_count():
    game = {'game_id':'x','player_name':'t','phase':'WAITING_FOR_CHECKPOINT_3','reached':[],
            'deadline':None,'boosts':{},'message_queue':[], 'last_location':None}
    for i in (1,2,4,5):
        cp=GAME_CONFIG['checkpoints'][i]
        process_location(game,cp['latitude'],cp['longitude'],5)
    assert game['phase']=='WAITING_FOR_CHECKPOINT_3'
    assert game['reached']==[]
