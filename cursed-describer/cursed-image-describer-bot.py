# coding: utf-8

# In[ ]:


import math, os, twitter, random, requests, time
from keys import msft_cognitive_api_key, consumer_key, consumer_secret, access_token_key, access_token_secret, user_agent

download_images = False
img_folder = 'img'
screen_names = ['cursedimages', 'cursedimages_2']
delay_filepath = 'delay.tmp'


# In[ ]:


# delay script execution by number of seconds in delay_filepath
with open(delay_filepath, 'r') as file:
    start_delay = float(file.readline())
time.sleep(start_delay)


# In[ ]:


api = twitter.Api(consumer_key=consumer_key,
                  consumer_secret=consumer_secret,
                  access_token_key=access_token_key,
                  access_token_secret=access_token_secret)
user = api.VerifyCredentials().AsDict()
print('logged into twitter as "{}" id="{}"'.format(user['screen_name'], user['id']))


# ## Download all images tweeted by list of users, if so configured

# In[ ]:


if download_images:

    for screen_name in screen_names:

        max_count = 200 #twitter only lets you get 200 statuses at a time
        max_id = None
        statuses = []

        # how many statuses has this user posted?
        user = api.GetUser(screen_name=screen_name)
        count = user.statuses_count
        calls = math.ceil(count / max_count)

        # get all of the user's statuses, one batch at a time
        for _ in range(calls):
            batch = api.GetUserTimeline(screen_name=screen_name, count=max_count, max_id=max_id)
            statuses.extend(batch)
            max_id = batch[-1].id

        # for each status, download and save the media
        for status in statuses:
            if status.media is not None:
                for item in status.media:
                    img_filepath = '{}/{}-{}-{}.jpg'.format(img_folder, screen_name, status.id, item.id)
                    if not os.path.exists(img_filepath):
                        img_url = item.media_url
                        response = requests.get(img_url)
                        with open(img_filepath, 'wb') as handler:
                            handler.write(response.content)


# ## Pick a random image and pass it to Microsoft

# In[ ]:


files = os.listdir(img_folder)
i = random.randint(0, len(files))
file = files[i]
filepath = '{}/{}'.format(img_folder, file)


# In[ ]:


# send to microsoft computer vision api to get text description
msft_url = 'https://westus.api.cognitive.microsoft.com/vision/v1.0/analyze'
params = {'visualFeatures' : 'Description',
          'language' : 'en'}
headers = {'Content-Type' : 'application/octet-stream',
           'Ocp-Apim-Subscription-Key' : msft_cognitive_api_key}
with open(filepath, mode='rb') as f:
    response = requests.post(msft_url, params=params, data=f, headers=headers)


# In[ ]:


response_data = response.json()
description = response_data['description']['captions'][0]['text']


# In[ ]:


screen_name, status_id, image_id = file.split('-')
tweet_url = 'https://twitter.com/{}/status/{}'.format(screen_name, status_id)
status = '{}. {}'.format(description.capitalize(), tweet_url)
print(status)


# ## Tweet image and description

# In[ ]:


result = api.PostUpdate(status=status, media=filepath)
print(result.created_at, result.text)


# In[ ]:
