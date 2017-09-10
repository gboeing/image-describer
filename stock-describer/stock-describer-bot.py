# coding: utf-8

# # Stock photo description bot
#
# Uses microsoft's cognitive vision api: https://azure.microsoft.com/en-us/services/cognitive-services/computer-vision/
#
# To describe random stock photos from unsplash: https://source.unsplash.com/random

# In[ ]:


import requests, json, twitter, os, time
from keys import msft_cognitive_api_key, consumer_key, consumer_secret, access_token_key, access_token_secret, user_agent


# In[ ]:


# randomized stock photo url
unsplash_url = 'https://source.unsplash.com/random'

# twitter needs image files <3mb and microsoft needs <4mb
max_file_size = 3e6 #3 megabytes in bytes

delay_filepath = 'delay.tmp'


# In[ ]:


# delay script execution by number of seconds in delay_filepath
with open(delay_filepath, 'r') as file:
    start_delay = float(file.readline())
time.sleep(start_delay)


# ## Get a random image from unsplash

# In[ ]:


headers = {'User-Agent' : user_agent}

# download random images until we get one smaller than the max file size
file_size = max_file_size + 1
while file_size > max_file_size:
    response = requests.get(unsplash_url, headers=headers)
    img_data = response.content
    img_url = response.url
    ext = img_url[img_url.find('&fm=')+4 : img_url.find('&crop=')]
    img_filepath = 'img_temp.{}'.format(ext)

    with open(img_filepath, 'wb') as handler:
        handler.write(img_data)
    file_size = os.path.getsize(img_filepath)


# ## Get image description from microsoft computer vision API

# In[ ]:


# send to microsoft computer vision api to get text description
msft_url = 'https://westcentralus.api.cognitive.microsoft.com/vision/v1.0/analyze'
params = {'visualFeatures' : 'Description',
          'details' : 'Landmarks',
          'language' : 'en'}
headers = {'Content-Type' : 'application/json',
           'Ocp-Apim-Subscription-Key' : msft_cognitive_api_key}
data = json.dumps({'url':img_url})
response = requests.post(msft_url, params=params, data=data, headers=headers)


# In[ ]:


response_data = response.json()
description = response_data['description']['captions'][0]['text']
print(description, img_url)


# ## Tweet image and description

# In[ ]:


api = twitter.Api(consumer_key=consumer_key,
                  consumer_secret=consumer_secret,
                  access_token_key=access_token_key,
                  access_token_secret=access_token_secret)
user = api.VerifyCredentials().AsDict()
print('logged into twitter as "{}" id="{}"'.format(user['screen_name'], user['id']))


# In[ ]:


result = api.PostUpdate(status=description, media=img_url)
print(result.created_at, result.text)


# In[ ]:
