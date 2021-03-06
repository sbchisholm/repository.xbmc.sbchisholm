#
#  Copyright 2012 (Stephen B Chisholm)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


import xbmc, xbmcaddon, xbmcplugin, xbmcgui
import json, urllib, os, sys, urlparse
from xml.etree.ElementTree import ElementTree

__XBMC_Revision__ = xbmc.getInfoLabel('System.BuildVersion')
__settings__      = xbmcaddon.Addon(id='plugin.audio.cbc-radio')
__home__          = __settings__.getAddonInfo('path')
__language__      = __settings__.getLocalizedString
__version__       = __settings__.getAddonInfo('version')
__cwd__           = __settings__.getAddonInfo('path')
__addonname__     = 'CBC Radio'
__addonid__       = 'plugin.audio.cbc-radio'
__author__        = 'Stephen B Chisholm'

def url_query_to_dict(url):
  ''' Returns the URL query args parsed into a dictionary '''
  param = {}
  if url:
    u = urlparse.urlparse(url)
    for q in u.query.split('&'):
      kvp = q.split('=')
      param[kvp[0]] = kvp[1]
  return param

def build_station_listing(stations):
  ''' Build the list of station for a category '''
  for station in stations:
    u = sys.argv[0] + '?' + urllib.urlencode({'stream':station['url']})
    liz = xbmcgui.ListItem(station['name'])
    xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]),
                                url = u, listitem = liz,
                                isFolder = False)

def build_category_listing(categories, parent_category = ''):
  ''' Build the list of categories or subcategories '''
  for category_item in categories:
    if parent_category:
      u = sys.argv[0] + '?category=' + urllib.quote(parent_category) \
                      + '&subcategory=' + urllib.quote(category_item['name'])
    else:
      u = sys.argv[0] + '?category=' + category_item['name']
    liz = xbmcgui.ListItem(category_item['name'])
    xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]),
                                url = u, listitem = liz,
                                isFolder = True)

def main():
  ''' main entry point where the request are handled '''
  params = url_query_to_dict(sys.argv[2])
  category = params.get('category')
  subcategory = params.get('subcategory')
  stream = params.get('stream')
  station_data = json.loads(open(os.path.join(__home__, 'stations.json'), 'r').read())

  if stream:
    #play stream
    stream = urllib.url2pathname(stream)
    xbmc.Player().play(stream)

  elif category and subcategory:
    # list all of the station in the subcategory
    category = urllib.unquote(category)
    subcategory = urllib.unquote(subcategory)
    for category_item in station_data['categories']:
      if category_item['name'] == category:
        for subcategory_item in category_item['subcategories']:
          if subcategory_item['name'] == subcategory:
            build_station_listing(subcategory_item['stations'])
            break
        break
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

  elif category:
    # list all the stations or subcategories in the category
    category = urllib.unquote(category)
    for category_item in station_data['categories']:
      if category_item['name'] == category:
        if category_item.has_key('stations'):
          build_station_listing(category_item['stations'])
        else:
          build_category_listing(categories = category_item['subcategories'],
                                 parent_category = category)
        break
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

  else:
    # list all of the categories
    build_category_listing(station_data['categories'])
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

# Enter here.
main()
