
# coding: utf-8

# # City description bot
# 
# Uses microsoft's cognitive vision api: https://azure.microsoft.com/en-us/services/cognitive-services/computer-vision/
# 
# To describe popular photos of cities from reddit: https://www.reddit.com/r/cityporn/top

# In[ ]:


import requests, json, twitter, os, time
from keys import msft_cognitive_api_key, consumer_key, consumer_secret, access_token_key, access_token_secret, user_agent


# In[ ]:


url = 'https://www.reddit.com/r/cityporn/top.json' #or https://source.unsplash.com/random
history_filepath = 'history.txt'
delay_filepath = 'delay.tmp'

# twitter needs image files <3mb and microsoft needs <4mb
max_file_size = 3e6 #3 megabytes in bytes


# In[ ]:


with open(history_filepath, 'r') as f:
    history = [s.strip() for s in f.readlines()]


# In[ ]:


# delay script execution by number of seconds in delay_filepath
with open(delay_filepath, 'r') as file:
    start_delay = float(file.readline())
time.sleep(start_delay)


# ## Get list of current top images from reddit, and filter them

# In[ ]:


headers = {'User-Agent' : user_agent}
response = requests.get(url, headers=headers)
posts = response.json()['data']['children']
images = []
for post in posts:
    post_id = post['data']['name']
    post_title = post['data']['title']
    post_url = post['data']['url']
    images.append({'id':post_id, 'url':post_url, 'title':post_title})
print(len(images))


# In[ ]:


# only use images with valid file extensions
def filter_url(url, extensions=['jpg','png']):
    is_valid = False    
    for ext in extensions:
        if url.endswith(ext):
            is_valid = True           
    return is_valid

images = [image for image in images if filter_url(image['url'])]
print(len(images))


# In[ ]:


# only use images we haven't used before
def filter_history(link_id):
    return not link_id in history

images = [image for image in images if filter_history(image['id'])]
print(len(images))


# ## Download image

# In[ ]:


def download_img(url, img_filepath='img_temp.{}', mode='wb'):
    extension = url[url.rfind('.')+1:]
    img_filepath = img_filepath.format(extension)
    img_data = requests.get(url, headers=headers).content
    with open(img_filepath, mode) as handler:
        handler.write(img_data)
    return img_filepath


# In[ ]:


# of the images that remain after filtering, grab the first that is smaller than max_file_size
for image in images:
    img_filepath = download_img(image['url'])
    if os.path.getsize(img_filepath) < max_file_size:
        break


# ## Get image description from microsoft computer vision API

# In[ ]:


# send to microsoft computer vision api to get text description
url = 'https://westcentralus.api.cognitive.microsoft.com/vision/v1.0/analyze'
params = {'visualFeatures' : 'Description',
          'details' : 'Landmarks',
          'language' : 'en'}
headers = {'Content-Type' : 'application/json',
           'Ocp-Apim-Subscription-Key' : msft_cognitive_api_key}
data = json.dumps({'url':image['url']})
response = requests.post(url, params=params, data=data, headers=headers)


# In[ ]:


response_data = response.json()
description = response_data['description']['captions'][0]['text']
print(description, image['url'])


# ## Tweet image and description

# In[ ]:


api = twitter.Api(consumer_key=consumer_key,
                  consumer_secret=consumer_secret,
                  access_token_key=access_token_key,
                  access_token_secret=access_token_secret)
user = api.VerifyCredentials().AsDict()
print('logged into twitter as "{}" id={}'.format(user['screen_name'], user['id']))


# In[ ]:


result = api.PostUpdate(status=description, media=img_filepath)
print(result.created_at, result.text)


# ## Clean up

# In[ ]:


# update history with this post id
history.append(image['id'])
history = list(set(history))
with open(history_filepath, 'w') as f:
    f.write('\n'.join(history))


# In[ ]:




