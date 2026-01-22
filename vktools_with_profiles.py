from vk_api import VkTools, VkToolsException
from vk_api.execute import VkFunction

from profile_cache import ProfileCache

vk_get_all_items = VkFunction(
    args=('method', 'key', 'values', 'count', 'offset', 'offset_mul'),
    clean_args=('method', 'key', 'offset', 'offset_mul'),
    return_raw=True,
    code='''
    var params = %(values)s,
        calls = 0,
        items = [],
        profiles = [],
        groups = [],
        count = %(count)s,
        offset = %(offset)s,
        ri;

    while(calls < 25) {
        calls = calls + 1;

        params.offset = offset * %(offset_mul)s;
        var response = API.%(method)s(params),
            new_count = response.count,
            count_diff = (count == null ? 0 : new_count - count);
        if (!response) {
            return {"_error": 1};
        }

        if (count_diff < 0) {
            offset = offset + count_diff;
        } else {
            ri = response.%(key)s;
            items = items + ri.slice(count_diff);
            profiles = profiles + response.profiles;
            groups = groups + response.groups;
            offset = offset + params.count + count_diff;
            if (ri.length < params.count) {
                calls = 99;
            }
        }

        count = new_count;

        if (count != null && offset >= count) {
            calls = 99;
        }
    };

    return {
        count: count,
        items: items,
        profiles: profiles,
        groups: groups,
        offset: offset,
        more: calls != 99
    };
''')


class VkToolsWithProfiles(VkTools):
    def get_all(self, method, max_count, values=None, key='items', limit=None,
                stop_fn=None, negative_offset=False, profile_cache: ProfileCache = None):
        items = []

        values = values.copy() if values else {}
        values['count'] = max_count

        offset = max_count if negative_offset else 0
        items_count = 0
        count = None

        while True:
            response = vk_get_all_items(
                self.vk, method, key, values, count, offset,
                offset_mul=-1 if negative_offset else 1
            )

            if 'execute_errors' in response:
                raise VkToolsException(
                    'Could not load items: {}'.format(
                        response['execute_errors']
                    ),
                    response=response
                )

            response = response['response']

            new_items = response["items"]
            items_count += len(new_items)

            items += new_items
            if profile_cache is not None and 'profiles' in response:
                profile_cache.cache_profiles(response['profiles'])
            if profile_cache is not None and 'groups' in response:
                profile_cache.cache_groups(response['groups'])

            if not response['more']:
                break

            if limit and items_count >= limit:
                break

            if stop_fn and stop_fn(new_items):
                break

            count = response['count']
            offset = response['offset']

        return {
            key: items,
            'profiles': profile_cache.profiles if profile_cache is not None else [],
            'groups': profile_cache.groups if profile_cache is not None else [],
        }