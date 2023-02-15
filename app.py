import datetime
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

# ----------------------------------------------------------------------------------------------------

application = Flask(__name__)

catalogueCollectionUrl = 'https://openactive.io/data-catalogs/data-catalog-collection.jsonld'

# ----------------------------------------------------------------------------------------------------

def try_requests(url):

    r = requests.get(url)

    numTries = 1
    numTriesMax = 10

    while (r.status_code == 403):
        r = requests.get(url)
        numTries += 1
        if (numTries == numTriesMax):
            break;

    return r

# ----------------------------------------------------------------------------------------------------

catalogueUrls = {
    'metadata': {
        'counts': 0,
        'timeLastUpdated': None,
    },
    'data': [],
}
@application.route('/catalogueurls')
def get_catalogueUrls(
    doRefresh = None
):

    doRefresh = request.args.get('refresh', default=False, type=lambda arg: arg.lower()=='true')
    doMetadata = request.args.get('metadata', default=True, type=lambda arg: arg.lower()=='true')
    doFlatten = request.args.get('flatten', default=False, type=lambda arg: arg.lower()=='true')

    # ----------------------------------------------------------------------------------------------------

    if (    not catalogueUrls['metadata']['timeLastUpdated']
        or  doRefresh
    ):

        try:
            r1 = try_requests(catalogueCollectionUrl)
        except:
            print('ERROR: Can\'t get collection of catalogues')

        # ----------------------------------------------------------------------------------------------------

        if (    r1.status_code == 200
            and r1.json()
            and type(r1.json()) == dict
            and 'hasPart' in r1.json().keys()
            and type(r1.json()['hasPart']) == list
        ):
            for catalogueUrl in r1.json()['hasPart']: # Enable to do all catalogues
            # for catalogueUrl in [r1.json()['hasPart'][0]]: # Enable to do only one catalogue for a test
                if (    type(catalogueUrl) == str
                    and catalogueUrl not in catalogueUrls['data']
                ):
                    catalogueUrls['data'].append(catalogueUrl)

        # ----------------------------------------------------------------------------------------------------

        catalogueUrls['metadata']['counts'] = len(catalogueUrls['data'])
        catalogueUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

    # ----------------------------------------------------------------------------------------------------

    if (    doFlatten
        or  not doMetadata
    ):
        return json.dumps(catalogueUrls['data'])
    else:
        return json.dumps(catalogueUrls)

# ----------------------------------------------------------------------------------------------------

datasetUrls = {
    'metadata': {
        'counts': 0,
        'timeLastUpdated': None,
    },
    'data': {},
}
@application.route('/dataseturls')
def get_datasetUrls(
    doRefresh = None
):

    doRefresh = request.args.get('refresh', default=False, type=lambda arg: arg.lower()=='true')
    doMetadata = request.args.get('metadata', default=True, type=lambda arg: arg.lower()=='true')
    doFlatten = request.args.get('flatten', default=False, type=lambda arg: arg.lower()=='true')

    # ----------------------------------------------------------------------------------------------------

    if (    not datasetUrls['metadata']['timeLastUpdated']
        or  doRefresh
    ):

        get_catalogueUrls(doRefresh)

        # ----------------------------------------------------------------------------------------------------

        for catalogueUrl in catalogueUrls['data']:

            catalogueDatasetUrls = {
                'metadata': {
                    'counts': 0,
                    'timeLastUpdated': None,
                },
                'data': [],
            }

            # ----------------------------------------------------------------------------------------------------

            try:
                r2 = try_requests(catalogueUrl)
            except:
                print('ERROR: Can\'t get catalogue', catalogueUrl)
                continue

            # ----------------------------------------------------------------------------------------------------

            if (    r2.status_code == 200
                and r2.json()
                and type(r2.json()) == dict
                and 'dataset' in r2.json().keys()
                and type(r2.json()['dataset']) == list
            ):
                for datasetUrl in r2.json()['dataset']: # Enable to do all datasets
                # for datasetUrl in [r2.json()['dataset'][0]]: # Enable to do only one dataset for a test
                    if (    type(datasetUrl) == str
                        and datasetUrl not in catalogueDatasetUrls['data']
                    ):
                        catalogueDatasetUrls['data'].append(datasetUrl)

            # ----------------------------------------------------------------------------------------------------

            catalogueDatasetUrls['metadata']['counts'] = len(catalogueDatasetUrls['data'])
            catalogueDatasetUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

            datasetUrls['data'][catalogueUrl] = catalogueDatasetUrls

        # ----------------------------------------------------------------------------------------------------

        datasetUrls['metadata']['counts'] = sum([
            val['metadata']['counts']
            for val in datasetUrls['data'].values()
        ])
        datasetUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

    # ----------------------------------------------------------------------------------------------------

    if (doFlatten):
        return json.dumps([
            val2
            for val1 in datasetUrls['data'].values()
            for val2 in val1['data']
        ])
    elif (not doMetadata):
        return json.dumps({
            key: val['data']
            for key,val in datasetUrls['data'].items()
        })
    else:
        return json.dumps(datasetUrls)

# ----------------------------------------------------------------------------------------------------

feedUrls = {
    'metadata': {
        'counts': 0,
        'timeLastUpdated': None,
    },
    'data': {},
}
@application.route('/feedurls')
def get_feedUrls(
    doRefresh = None
):

    doRefresh = request.args.get('refresh', default=False, type=lambda arg: arg.lower()=='true')
    doMetadata = request.args.get('metadata', default=True, type=lambda arg: arg.lower()=='true')
    doFlatten = request.args.get('flatten', default=False, type=lambda arg: arg.lower()=='true')

    # ----------------------------------------------------------------------------------------------------

    if (    not feedUrls['metadata']['timeLastUpdated']
        or  doRefresh
    ):

        get_datasetUrls(doRefresh)

        # ----------------------------------------------------------------------------------------------------

        for catalogueUrl,catalogueDatasetUrls in datasetUrls['data'].items():

            feedUrls['data'][catalogueUrl] = {
                'metadata': {
                    'counts': 0,
                    'timeLastUpdated': None,
                },
                'data': {},
            }

            # ----------------------------------------------------------------------------------------------------

            for datasetUrl in catalogueDatasetUrls['data']:

                datasetFeedUrls = {
                    'metadata': {
                        'counts': 0,
                        'timeLastUpdated': None,
                    },
                    'data': [],
                }

                # ----------------------------------------------------------------------------------------------------

                try:
                    r3 = try_requests(datasetUrl)
                except:
                    print('ERROR: Can\'t get dataset', catalogueUrl, '->', datasetUrl)
                    continue

                # ----------------------------------------------------------------------------------------------------

                if (    r3.status_code == 200
                    and r3.text
                    and type(r3.text) == str
                ):

                    soup = BeautifulSoup(r3.text, 'html.parser')

                    if (not soup.head):
                        continue

                    for val in soup.head.find_all('script'):
                        if (    'type' in val.attrs.keys()
                            and val['type'] == 'application/ld+json'
                        ):

                            jsonld = json.loads(val.string)

                            if (    type(jsonld) == dict
                                and 'distribution' in jsonld.keys()
                                and type(jsonld['distribution']) == list
                            ):
                                for jsonldDistribution in jsonld['distribution']: # Enable to do all feeds
                                # for jsonldDistribution in [jsonld['distribution'][0]]: # Enable to do only one feed for a test
                                    if (    type(jsonldDistribution) == dict
                                        and 'contentUrl' in jsonldDistribution.keys()
                                        and type(jsonldDistribution['contentUrl']) == str
                                        and jsonldDistribution['contentUrl'] not in datasetFeedUrls['data']
                                    ):
                                        datasetFeedUrls['data'].append(jsonldDistribution['contentUrl'])

                # ----------------------------------------------------------------------------------------------------

                datasetFeedUrls['metadata']['counts'] = len(datasetFeedUrls['data'])
                datasetFeedUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

                feedUrls['data'][catalogueUrl]['data'][datasetUrl] = datasetFeedUrls

            # ----------------------------------------------------------------------------------------------------

            feedUrls['data'][catalogueUrl]['metadata']['counts'] = sum([
                val['metadata']['counts']
                for val in feedUrls['data'][catalogueUrl]['data'].values()
            ])
            feedUrls['data'][catalogueUrl]['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

        # ----------------------------------------------------------------------------------------------------

        feedUrls['metadata']['counts'] = sum([
            val['metadata']['counts']
            for val in feedUrls['data'].values()
        ])
        feedUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

    # ----------------------------------------------------------------------------------------------------

    if (doFlatten):
        return json.dumps([
            val3
            for val1 in feedUrls['data'].values()
            for val2 in val1['data'].values()
            for val3 in val2['data']
        ])
    elif (not doMetadata):
        return json.dumps({
            key1: {
                key2: val2['data']
                for key2,val2 in val1['data'].items()
            }
            for key1,val1 in feedUrls['data'].items()
        })
    else:
        return json.dumps(feedUrls)

# ----------------------------------------------------------------------------------------------------

feeds = {
    'metadata': {
        'counts': 0,
        'timeLastUpdated': None,
    },
    'data': {},
}
@application.route('/feeds')
def get_feeds(
    doRefresh = None
):

    doRefresh = request.args.get('refresh', default=False, type=lambda arg: arg.lower()=='true')
    doMetadata = request.args.get('metadata', default=True, type=lambda arg: arg.lower()=='true')
    doFlatten = request.args.get('flatten', default=False, type=lambda arg: arg.lower()=='true')

    # ----------------------------------------------------------------------------------------------------

    if (    not feeds['metadata']['timeLastUpdated']
        or  doRefresh
    ):

        get_datasetUrls(doRefresh)

        # ----------------------------------------------------------------------------------------------------

        for catalogueUrl,catalogueDatasetUrls in datasetUrls['data'].items():

            feeds['data'][catalogueUrl] = {
                'metadata': {
                    'counts': 0,
                    'timeLastUpdated': None,
                },
                'data': {},
            }

            # ----------------------------------------------------------------------------------------------------

            for datasetUrl in catalogueDatasetUrls['data']:

                datasetFeedUrls = {
                    'metadata': {
                        'counts': 0,
                        'timeLastUpdated': None,
                    },
                    'data': [],
                }

                # ----------------------------------------------------------------------------------------------------

                try:
                    r3 = try_requests(datasetUrl)
                except:
                    print('ERROR: Can\'t get dataset', catalogueUrl, '->', datasetUrl)
                    continue

                # ----------------------------------------------------------------------------------------------------

                if (    r3.status_code == 200
                    and r3.text
                    and type(r3.text) == str
                ):

                    soup = BeautifulSoup(r3.text, 'html.parser')

                    if (not soup.head):
                        continue

                    for val in soup.head.find_all('script'):
                        if (    'type' in val.attrs.keys()
                            and val['type'] == 'application/ld+json'
                        ):

                            jsonld = json.loads(val.string)

                            if (    type(jsonld) == dict
                                and 'distribution' in jsonld.keys()
                                and type(jsonld['distribution']) == list
                            ):
                                for jsonldDistribution in jsonld['distribution']: # Enable to do all feeds
                                # for jsonldDistribution in [jsonld['distribution'][0]]: # Enable to do only one feed for a test
                                    if (type(jsonldDistribution) == dict):

                                        feed = {}

                                        feed['feedUrl'] = jsonldDistribution['contentUrl'] if ('contentUrl' in jsonldDistribution.keys()) else ''
                                        feed['feedName'] = jsonldDistribution['name'] if ('name' in jsonldDistribution.keys()) else ''
                                        # Should match datasetUrl from r2.json()['dataset']:
                                        feed['datasetUrl'] = jsonld['url'] if ('url' in jsonld.keys()) else ''
                                        feed['datasetName'] = jsonld['name'] if ('name' in jsonld.keys()) else ''
                                        feed['datasetPublisherName'] = jsonld['publisher']['name'] if ('publisher' in jsonld.keys()) and (type(jsonld['publisher']) == dict) and ('name' in jsonld['publisher'].keys()) else ''
                                        # # Should match catalogueUrl from r1.json()['hasPart']:
                                        # feed['catalogueUrl'] = r2.json()['id'] if ('id' in r2.json().keys()) else r2.json()['@id'] if ('@id' in r2.json().keys()) else ''
                                        # # The catalogue publisher name is the closest we have to a catalogue name proper:
                                        # feed['cataloguePublisherName'] = r2.json()['publisher']['name'] if ('publisher' in r2.json().keys()) and (type(r2.json()['publisher']) == dict) and ('name' in r2.json()['publisher'].keys()) else ''
                                        feed['discussionUrl'] = jsonld['discussionUrl'] if ('discussionUrl' in jsonld.keys()) else ''
                                        feed['licenseUrl'] = jsonld['license'] if ('license' in jsonld.keys()) else ''

                                        datasetFeedUrls['data'].append(feed)

                # ----------------------------------------------------------------------------------------------------

                datasetFeedUrls['metadata']['counts'] = len(datasetFeedUrls['data'])
                datasetFeedUrls['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

                feeds['data'][catalogueUrl]['data'][datasetUrl] = datasetFeedUrls

            # ----------------------------------------------------------------------------------------------------

            feeds['data'][catalogueUrl]['metadata']['counts'] = sum([
                val['metadata']['counts']
                for val in feeds['data'][catalogueUrl]['data'].values()
            ])
            feeds['data'][catalogueUrl]['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

        # ----------------------------------------------------------------------------------------------------

        feeds['metadata']['counts'] = sum([
            val['metadata']['counts']
            for val in feeds['data'].values()
        ])
        feeds['metadata']['timeLastUpdated'] = str(datetime.datetime.now())

    # ----------------------------------------------------------------------------------------------------

    if (doFlatten):
        return json.dumps([
            val3
            for val1 in feeds['data'].values()
            for val2 in val1['data'].values()
            for val3 in val2['data']
        ])
    elif (not doMetadata):
        return json.dumps({
            key1: {
                key2: val2['data']
                for key2,val2 in val1['data'].items()
            }
            for key1,val1 in feeds['data'].items()
        })
    else:
        return json.dumps(feeds)

# ----------------------------------------------------------------------------------------------------

@application.route('/feeds_v1')
def get_feeds_v1():

    feeds_v1 = []

    # ----------------------------------------------------------------------------------------------------

    try:
        r1 = try_requests(catalogueCollectionUrl)
    except:
        print('ERROR: Can\'t get collection of catalogues')

    # ----------------------------------------------------------------------------------------------------

    if (    r1.status_code == 200
        and r1.json()
        and type(r1.json()) == dict
        and 'hasPart' in r1.json().keys()
        and type(r1.json()['hasPart']) == list
    ):
        for catalogueUrl in r1.json()['hasPart']: # Enable to do all catalogues
        # for catalogueUrl in [r1.json()['hasPart'][0]]: # Enable to do only one catalogue for a test
            if (type(catalogueUrl) == str):

                try:
                    r2 = try_requests(catalogueUrl)
                except:
                    print('ERROR: Can\'t get catalogue', catalogueUrl)
                    continue

                # ----------------------------------------------------------------------------------------------------

                if (    r2.status_code == 200
                    and r2.json()
                    and type(r2.json()) == dict
                    and 'dataset' in r2.json().keys()
                    and type(r2.json()['dataset']) == list
                ):
                    for datasetUrl in r2.json()['dataset']: # Enable to do all datasets
                    # for datasetUrl in [r2.json()['dataset'][0]]: # Enable to do only one dataset for a test
                        if (type(datasetUrl) == str):

                            try:
                                r3 = try_requests(datasetUrl)
                            except:
                                print('ERROR: Can\'t get dataset', catalogueUrl, '->', datasetUrl)
                                continue

                            # ----------------------------------------------------------------------------------------------------

                            if (    r3.status_code == 200
                                and r3.text
                                and type(r3.text) == str
                            ):

                                soup = BeautifulSoup(r3.text, 'html.parser')

                                if (not soup.head):
                                    continue

                                for val in soup.head.find_all('script'):
                                    if (    'type' in val.attrs.keys()
                                        and val['type'] == 'application/ld+json'
                                    ):

                                        jsonld = json.loads(val.string)

                                        if (    type(jsonld) == dict
                                            and 'distribution' in jsonld.keys()
                                            and type(jsonld['distribution']) == list
                                        ):
                                            for jsonldDistribution in jsonld['distribution']: # Enable to do all feeds
                                            # for jsonldDistribution in [jsonld['distribution'][0]]: # Enable to do only one feed for a test
                                                if (type(jsonldDistribution) == dict):

                                                    feed = {}

                                                    feed['feedUrl'] = jsonldDistribution['contentUrl'] if ('contentUrl' in jsonldDistribution.keys()) else ''
                                                    feed['feedName'] = jsonldDistribution['name'] if ('name' in jsonldDistribution.keys()) else ''
                                                    # Should match datasetUrl from r2.json()['dataset']:
                                                    feed['datasetUrl'] = jsonld['url'] if ('url' in jsonld.keys()) else ''
                                                    feed['datasetName'] = jsonld['name'] if ('name' in jsonld.keys()) else ''
                                                    feed['datasetPublisherName'] = jsonld['publisher']['name'] if ('publisher' in jsonld.keys()) and (type(jsonld['publisher']) == dict) and ('name' in jsonld['publisher'].keys()) else ''
                                                    # Should match catalogueUrl from r1.json()['hasPart']:
                                                    feed['catalogueUrl'] = r2.json()['id'] if ('id' in r2.json().keys()) else r2.json()['@id'] if ('@id' in r2.json().keys()) else ''
                                                    # The catalogue publisher name is the closest we have to a catalogue name proper:
                                                    feed['cataloguePublisherName'] = r2.json()['publisher']['name'] if ('publisher' in r2.json().keys()) and (type(r2.json()['publisher']) == dict) and ('name' in r2.json()['publisher'].keys()) else ''
                                                    feed['discussionUrl'] = jsonld['discussionUrl'] if ('discussionUrl' in jsonld.keys()) else ''
                                                    feed['licenseUrl'] = jsonld['license'] if ('license' in jsonld.keys()) else ''
                                                    feed['numActivities'] = 0
                                                    feed['numActivitiesWithName1'] = 0
                                                    feed['numActivitiesWithName2'] = 0
                                                    feed['numActivitiesWithId'] = 0
                                                    feed['activities'] = []

                                                    # ----------------------------------------------------------------------------------------------------

                                                    if (    'contentUrl' in jsonldDistribution.keys()
                                                        and type(jsonldDistribution['contentUrl'] == str)
                                                    ):

                                                        feedUrl = jsonldDistribution['contentUrl']

                                                        try:
                                                            r4 = try_requests(feedUrl)
                                                        except:
                                                            print('ERROR: Can\'t get feed', catalogueUrl, '->', datasetUrl, '->', feedUrl)
                                                            continue

                                                        # ----------------------------------------------------------------------------------------------------

                                                        if (    r4.status_code == 200
                                                            and r4.json()
                                                            and type(r4.json()) == dict
                                                            and 'items' in r4.json().keys()
                                                            and type(r4.json()['items']) == list
                                                        ):

                                                            feed['numActivities'] = len(r4.json()['items'])

                                                            for feedActivity in r4.json()['items']:

                                                                activity = {}

                                                                if (    type(feedActivity) == dict
                                                                    and 'data' in feedActivity.keys()
                                                                    and type(feedActivity['data']) == dict
                                                                ):

                                                                    if (    'name' in feedActivity['data'].keys()
                                                                        and type(feedActivity['data']['name']) == str
                                                                    ):
                                                                        activity['name1'] = feedActivity['data']['name']
                                                                        feed['numActivitiesWithName1'] += 1

                                                                    if (    'beta:sportsActivityLocation' in feedActivity['data'].keys()
                                                                        and type(feedActivity['data']['beta:sportsActivityLocation']) == list
                                                                        and len(feedActivity['data']['beta:sportsActivityLocation']) == 1
                                                                        and type(feedActivity['data']['beta:sportsActivityLocation'][0]) == dict
                                                                        and 'name' in feedActivity['data']['beta:sportsActivityLocation'][0].keys()
                                                                        # and type(feedActivity['data']['beta:sportsActivityLocation'][0]['name']) == str # Sometimes this name field is a string, sometimes it is a list of strings ...
                                                                    ):
                                                                        activity['name2'] = feedActivity['data']['beta:sportsActivityLocation'][0]['name']
                                                                        feed['numActivitiesWithName2'] += 1

                                                                    if (    'activity' in feedActivity['data'].keys()
                                                                        and type(feedActivity['data']['activity']) == list
                                                                        and len(feedActivity['data']['activity']) == 1
                                                                        and type(feedActivity['data']['activity'][0]) == dict
                                                                        and 'id' in feedActivity['data']['activity'][0].keys()
                                                                        and type(feedActivity['data']['activity'][0]['id']) == str
                                                                    ):
                                                                        activity['id'] = feedActivity['data']['activity'][0]['id']
                                                                        feed['numActivitiesWithId'] += 1

                                                                if (len(activity.keys()) > 0):
                                                                    feed['activities'].append(activity)

                                                    # ----------------------------------------------------------------------------------------------------

                                                    feeds_v1.append(feed)

    # ----------------------------------------------------------------------------------------------------

    return json.dumps(feeds_v1)

# ----------------------------------------------------------------------------------------------------

@application.route('/keycounts')
def get_keycounts():

    keycounts = {
        'metadata': {
            'keysFeeds': {},
            'keysFeedsItemsData': {},
        },
        'catalogues': {},
    }

    # ----------------------------------------------------------------------------------------------------

    print('\rStep 1: Processing ...', end='')
    t1 = datetime.datetime.now()

    try:
        r1 = try_requests(catalogueCollectionUrl)
    except:
        print('\nERROR: Can\'t get collection of catalogues')

    t2 = datetime.datetime.now()
    print('\rStep 1: Time taken:', t2-t1)

    # ----------------------------------------------------------------------------------------------------

    print('\rStep 2: Processing ...', end='')
    t1 = datetime.datetime.now()

    if (    r1.status_code == 200
        and r1.json()
        and type(r1.json()) == dict
        and 'hasPart' in r1.json().keys()
        and type(r1.json()['hasPart']) == list
    ):
        for catalogueUrl in r1.json()['hasPart']: # Enable to do all catalogues
        # for catalogueUrl in [r1.json()['hasPart'][0]]: # Enable to do only one catalogue for a test
            if (    type(catalogueUrl) == str
                and catalogueUrl not in keycounts['catalogues'].keys()
            ):
                keycounts['catalogues'][catalogueUrl] = {
                    'metadata': {
                        'keysFeeds': {},
                        'keysFeedsItemsData': {},
                    },
                    'datasets': {},
                }

    t2 = datetime.datetime.now()
    print('\rStep 2: Time taken:', t2-t1)

    # ----------------------------------------------------------------------------------------------------

    print('\rStep 3: Processing ...', end='')
    t1 = datetime.datetime.now()

    for catalogueUrl,catalogue in keycounts['catalogues'].items():

        try:
            r2 = try_requests(catalogueUrl)
        except:
            print('\nERROR: Can\'t get catalogue', catalogueUrl)
            continue

        if (    r2.status_code == 200
            and r2.json()
            and type(r2.json()) == dict
            and 'dataset' in r2.json().keys()
            and type(r2.json()['dataset']) == list
        ):
            for datasetUrl in r2.json()['dataset']: # Enable to do all datasets
            # for datasetUrl in [r2.json()['dataset'][0]]: # Enable to do only one dataset for a test
                if (    type(datasetUrl) == str
                    and datasetUrl not in catalogue['datasets'].keys()
                ):
                    catalogue['datasets'][datasetUrl] = {
                        'metadata': {
                            'keysFeeds': {},
                            'keysFeedsItemsData': {},
                        },
                        'feeds': {},
                    }

    t2 = datetime.datetime.now()
    print('\rStep 3: Time taken:', t2-t1)

    # ----------------------------------------------------------------------------------------------------

    print('\rStep 4: Processing ...', end='')
    t1 = datetime.datetime.now()

    for catalogueUrl,catalogue in keycounts['catalogues'].items():
        for datasetUrl,dataset in catalogue['datasets'].items():

            try:
                r3 = try_requests(datasetUrl)
            except:
                print('\nERROR: Can\'t get dataset', catalogueUrl, '->', datasetUrl)
                continue

            if (    r3.status_code == 200
                and r3.text
                and type(r3.text) == str
            ):

                soup = BeautifulSoup(r3.text, 'html.parser')

                if (not soup.head):
                    continue

                for val in soup.head.find_all('script'):
                    if (    'type' in val.attrs.keys()
                        and val['type'] == 'application/ld+json'
                    ):

                        jsonld = json.loads(val.string)

                        if (    type(jsonld) == dict
                            and 'distribution' in jsonld.keys()
                            and type(jsonld['distribution']) == list
                        ):
                            for jsonldDistribution in jsonld['distribution']:
                                if (    type(jsonldDistribution) == dict
                                    and 'contentUrl' in jsonldDistribution.keys()
                                    and type(jsonldDistribution['contentUrl']) == str
                                    and jsonldDistribution['contentUrl'] not in dataset['feeds'].keys()
                                ):

                                    dataset['feeds'][jsonldDistribution['contentUrl']] = {
                                        'metadata': {
                                            'keys': list(jsonldDistribution.keys()),
                                        },
                                        'itemsData': {
                                            'metadata': {
                                                'keys': {},
                                            },
                                            'names': {},
                                        },
                                    }

                                    if (    'name' in jsonldDistribution.keys()
                                        and type(jsonldDistribution['name']) == str
                                    ):
                                        dataset['feeds'][jsonldDistribution['contentUrl']]['metadata']['name'] = jsonldDistribution['name']

    t2 = datetime.datetime.now()
    print('\rStep 4: Time taken:', t2-t1)

    # ----------------------------------------------------------------------------------------------------

    print('\rStep 5: Processing ...', end='')
    t1 = datetime.datetime.now()

    for catalogueUrl,catalogue in keycounts['catalogues'].items():
        for datasetUrl,dataset in catalogue['datasets'].items():
            for feedUrl,feed in dataset['feeds'].items():

                try:
                    r4 = try_requests(feedUrl)
                except:
                    print('\nERROR: Can\'t get feed', catalogueUrl, '->', datasetUrl, '->', feedUrl)
                    continue

                if (    r4.status_code == 200
                    and r4.json()
                    and type(r4.json()) == dict
                    and 'items' in r4.json().keys()
                    and type(r4.json()['items']) == list
                ):
                    # Each item is a different sporting activity:
                    for item in r4.json()['items']:
                        if (    type(item) == dict
                            and 'data' in item.keys()
                            and type(item['data']) == dict
                        ):

                            for key in item['data'].keys():
                                if (key not in feed['itemsData']['metadata']['keys'].keys()):
                                    feed['itemsData']['metadata']['keys'][key] = 1
                                else:
                                    feed['itemsData']['metadata']['keys'][key] += 1

                            if (    'name' in item['data'].keys()
                                and type(item['data']['name']) == str
                            ):
                                if (item['data']['name'] not in feed['itemsData']['names'].keys()):
                                    feed['itemsData']['names'][item['data']['name']] = 1
                                else:
                                    feed['itemsData']['names'][item['data']['name']] += 1

    t2 = datetime.datetime.now()
    print('\rStep 5: Time taken:', t2-t1)

    # ----------------------------------------------------------------------------------------------------

    for catalogue in keycounts['catalogues'].values():
        for dataset in catalogue['datasets'].values():
            for feed in dataset['feeds'].values():

                # ----------------------------------------------------------------------------------------------------

                for key in feed['metadata']['keys']:
                    if (key not in dataset['metadata']['keysFeeds'].keys()):
                        dataset['metadata']['keysFeeds'][key] = 1
                    else:
                        dataset['metadata']['keysFeeds'][key] += 1

                for key,val in feed['itemsData']['metadata']['keys'].items():
                    if (key not in dataset['metadata']['keysFeedsItemsData'].keys()):
                        dataset['metadata']['keysFeedsItemsData'][key] = val
                    else:
                        dataset['metadata']['keysFeedsItemsData'][key] += val

            # ----------------------------------------------------------------------------------------------------

            for superKey in ['keysFeeds', 'keysFeedsItemsData']:
                for key,val in dataset['metadata'][superKey].items():
                    if (key not in catalogue['metadata'][superKey].keys()):
                        catalogue['metadata'][superKey][key] = val
                    else:
                        catalogue['metadata'][superKey][key] += val

        # ----------------------------------------------------------------------------------------------------

        for superKey in ['keysFeeds', 'keysFeedsItemsData']:
            for key,val in catalogue['metadata'][superKey].items():
                if (key not in keycounts['metadata'][superKey].keys()):
                    keycounts['metadata'][superKey][key] = val
                else:
                    keycounts['metadata'][superKey][key] += val

    # ----------------------------------------------------------------------------------------------------

    return json.dumps(keycounts)

# ----------------------------------------------------------------------------------------------------

if (__name__ == '__main__'):
    application.run()
