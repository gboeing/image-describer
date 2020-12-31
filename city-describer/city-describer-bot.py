# City description bot by Geoff Boeing http://geoffboeing.com/
# Uses microsoft's cognitive vision api: https://azure.microsoft.com/en-us/services/cognitive-services/computer-vision/
# To describe popular photos of cities from reddit: https://www.reddit.com/r/cityporn/top
# uses the python-twitter package: pip install python-twitter


import json
import os
import requests
import sys
import time
import twitter
from PIL import Image
from keys import msft_cognitive_api_key, consumer_key, consumer_secret, access_token_key, access_token_secret, user_agent, google_places_api_key


# configure the script
download = True
download_on_retry = True #if local image fails, can we find a new one online?
tweet = True
reddit_url = 'https://www.reddit.com/r/CityPorn/top.json?sort=top&t=day'
history_filepath = 'history.txt'
delay_filepath = 'delay.tmp'
max_retries = 6 #try up to 3 different images, plus 1 attempted re-size each

# twitter needs image files <3mb and microsoft needs <4mb
max_file_size = 3e6 #3 megabytes in bytes
max_dimensions = (1500, 1500) # if file exceeds max_file_size, resize to this max


# only use images with valid file extensions
def filter_url(url, extensions=['jpg','png']):
    is_valid = False
    for ext in extensions:
        if url.endswith(ext):
            is_valid = True
    return is_valid


# download the image file from its server
def download_img(url, headers, img_filepath='img_temp.{}', mode='wb'):
    extension = url[url.rfind('.')+1:]
    img_filepath = img_filepath.format(extension)
    img_data = requests.get(url, headers=headers).content
    with open(img_filepath, mode) as handler:
        handler.write(img_data)
    return img_filepath


# resize an image file to some max dimensions
def resize_img_file(img_filepath, max_dimensions=max_dimensions):
    original_image = Image.open(img_filepath)
    img_format = original_image.format
    img = original_image.copy()
    img.thumbnail((max_dimensions[0], max_dimensions[1]), Image.LANCZOS)
    img.format = img_format
    img.save(img_filepath)
    print('resized the image file from {} to {}'.format(original_image.size, img.size))


# download an image from reddit
def get_img_from_reddit(reddit_url=reddit_url, history_filepath=history_filepath,
                        max_file_size=max_file_size):

    # open the history file of previously used reddit posts
    with open(history_filepath, 'r') as f:
        history = [s.strip() for s in f.readlines()]

    # get list of current top images from reddit
    headers = {'User-Agent' : user_agent}
    response = requests.get(reddit_url, headers=headers)
    posts = response.json()['data']['children']
    images = []
    for post in posts:
        post_id = post['data']['name']
        post_title = post['data']['title']
        post_url = post['data']['url']
        images.append({'id':post_id, 'url':post_url, 'title':post_title})
    print('found {} total images'.format(len(images)))

    # filter images to retain only those with .jpg or .png file extensions
    images = [image for image in images if filter_url(image['url'])]
    print('{} of them are .jpg or .png files'.format(len(images)))

    # only use images we haven't used before
    images = [image for image in images if not image['id'] in history]
    print('{} of them have not already been used'.format(len(images)))

    if len(images) < 1:
        print('there are no new images to use, so exit the script')
        sys.exit()

    # of the images that remain after filtering, grab the first that is smaller
    # than max_file_size, or that we can resize to be small enough
    for image in images:
        img_filepath = download_img(image['url'], headers=headers)
        if os.path.getsize(img_filepath) < max_file_size:
            break #if this image is small enough, break the loop and use it
        else:
            # if this image is too big, try to resize it then check it again
            resize_img_file(img_filepath)
            if os.path.getsize(img_filepath) < max_file_size:
                break #if this image is now small enough, break the loop and use it

    # update history with this post id
    history.append(image['id'])
    history = list(set(history))
    with open(history_filepath, 'w') as f:
        f.write('\n'.join(history))

    return image['url'], img_filepath, image['title']


# geocode a query
def geocode(query):
    url = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&address={}&sensor=false'
    url = url.format(google_places_api_key, query)
    return requests.get(url).json()


# parse an image title into a geocodable query
def parse_title(title):

    query = title.lower()

    if '[' in query:
        query = query.split('[')[0].strip()
    if '(' in query:
        query = query.split('(')[0].strip()
    if ' in ' in query:
        query = query.split(' in ')[1].strip()

    query = query.replace('|', ' ').replace('-', ' ').replace('  ', ' ').replace('  ', ' ').strip(' ,.')
    return query


# turn an image title into location info
def get_location(img_title):

    query = parse_title(img_title)
    data = geocode(query)
    if len(data['results']) > 0:
        result = data['results'][0]

        place = result['formatted_address'].lower()
        place = place.strip('0123456789').strip(' ,.')

        lat = result['geometry']['location']['lat']
        lng = result['geometry']['location']['lng']

        return lat, lng, place



# run the script
def run(attempt=0, download=download, max_dimensions=max_dimensions, img_title=None):

    attempt += 1

    try:
        if download and download_on_retry:
            # download an image file from reddit and get its url and local path
            img_url, img_filepath, img_title = get_img_from_reddit()
        else:
            # else, just use an existing temp image
            img_url = ''
            img_filepath = 'img_temp.jpg'
            try:
                # try to read a place name from img_title.txt file
                with open('img_title.txt','r') as f:
                    img_title = f.read()
            except:
                img_title = None


        # upload image to microsoft computer vision api to get text description
        url = 'https://westus.api.cognitive.microsoft.com/vision/v1.0/analyze'
        params = {'visualFeatures' : 'Description',
                  'details' : 'Landmarks',
                  'language' : 'en'}
        headers = {'User-Agent' : user_agent,
                   'Content-Type' : 'application/octet-stream',
                   'Ocp-Apim-Subscription-Key' : msft_cognitive_api_key}
        img_data = open(img_filepath, mode='rb').read()
        response = requests.post(url, params=params, data=img_data, headers=headers)
        response_data = response.json()
        description = response_data['description']['captions'][0]['text']
        print(description, img_url)

        # if we have an image title, try to geocode it
        lat = None
        lng = None
        if img_title:
            try:
                lat, lng, place = get_location(img_title)
                #maps_url = 'https://www.google.com/maps/search/{},{}'.format(lat, lng)
                #location_status = 'where is this? my guess is {} {}'.format(place, maps_url)
                print('latlng = {},{}'.format(lat, lng))
            except Exception as e:
                print('could not get location')


        # log into twitter as the bot
        api = twitter.Api(consumer_key=consumer_key,
                          consumer_secret=consumer_secret,
                          access_token_key=access_token_key,
                          access_token_secret=access_token_secret)
        user = api.VerifyCredentials().AsDict()
        print('logged into twitter as "{}" id={}'.format(user['screen_name'], user['id']))


        if tweet:
            # tweet image and its text description
            if lat is None or lng is None:
                result = api.PostUpdate(status=description, media=img_filepath)
            else:
                result = api.PostUpdate(status=description, media=img_filepath, latitude=lat, longitude=lng, display_coordinates=True)

            print(result.created_at, result.text)


    except Exception as e:

        print('error:', e)

        if attempt < max_retries:

            # on even numbered attempts, try re-sizing image
            if (attempt + 1) % 2 == 0:

                print('trying again by re-sizing the image file (attempt {} of {})...'.format(attempt + 1, max_retries))
                new_dimensions = [int(d * 0.9) for d in max_dimensions]
                resize_img_file(img_filepath, new_dimensions)
                run(attempt=attempt, download=False, max_dimensions=new_dimensions, img_title=img_title)

            # on odd numbered attempts, try a different image
            else:
                print('trying again with a new image (attempt {} of {})...'.format(attempt + 1, max_retries))
                run(attempt=attempt, download=True)

        else:
            print('no more re-tries, giving up')




###############################################################################
# start script execution
###############################################################################


# delay script execution by number of seconds in delay_filepath
with open(delay_filepath, 'r') as file:
    start_delay = float(file.readline())
print('script will start after a {:,.1f} second delay'.format(start_delay))
time.sleep(start_delay)


run()


# all done
print('script finished')
