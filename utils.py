from vk_api import VkTools

def get_likes(tools: VkTools, owner_id, item_type, item_id, profile_cache):
    likers = tools.get_all(
        method='likes.getList',
        max_count=100,
        values={
            'type': item_type,
            'owner_id': owner_id,
            'item_id': item_id,
            'extended': 1,
            'fields': PROFILE_FIELDS,
        },
    )

    liked_ids = []
    for liker in likers['items']:
        if liker['type'] == 'profile':
            del liker['type']
            liked_ids.append(liker['id'])
            profile_cache.cache_profile(liker)
        elif liker['type'] == 'group':
            del liker['type']
            liked_ids.append(-abs(liker['id']))
            liker['id'] = abs(liker['id'])
            profile_cache.cache_group(liker)
        else:
            continue

    return liked_ids


PROFILE_FIELDS = ('about,'
                  'activities,'
                  'activity,'
                  'addresses,'
                  'bdate,'
                  'blacklisted,'
                  'blacklisted_by_me,'
                  'books,'
                  'career,'
                  'city,'
                  'common_count,'
                  'connections,'
                  'contacts,'
                  'country,'
                  'crop_photo,'
                  'domain,'
                  'description,'
                  'education,'
                  'exports,'
                  'fixed_post,'
                  'followers_count,'
                  'games,'
                  'has_mobile,'
                  'has_photo,'
                  'home_town,'
                  'interests,'
                  'is_favorite,'
                  'is_hidden_from_feed,'
                  'is_no_index,'
                  'last_seen,'
                  'links,'
                  'main_album_id,'
                  'maiden_name,'
                  'member_status,'
                  'military,'
                  'movies,'
                  'music,'
                  'nickname,'
                  'occupation,'
                  'personal,'
                  'photo_id',
                  'photo_400_orig,'
                  'photo_max_orig,'
                  'place,'
                  'public_date_label,'
                  'start_date,'
                  'finish_date,'
                  'quotes,'
                  'relatives,'
                  'relation,'
                  'schools,'
                  'screen_name,'
                  'sex,'
                  'site,'
                  'status,'
                  'tv,'
                  'universities,'
                  'verified,'
                  'wall_default')
