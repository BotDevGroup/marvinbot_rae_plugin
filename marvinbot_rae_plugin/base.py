# -*- coding: utf-8 -*-

from marvinbot.utils import localized_date, get_message
from marvinbot.handlers import CommandHandler, CallbackQueryHandler
from marvinbot.plugins import Plugin
from marvinbot.models import User

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bs4 import BeautifulSoup

import logging
import re
import requests
import ctypes

log = logging.getLogger(__name__)


class MarvinBotRaePlugin(Plugin):
    def __init__(self):
        super(MarvinBotRaePlugin, self).__init__('marvinbot_rae_plugin')
        self.bot = None

    def get_default_config(self):
        return {
            'short_name': self.name,
            'enabled': True,
            'base_url': 'http://dle.rae.es'
        }

    def configure(self, config):
        self.config = config
        pass

    def setup_handlers(self, adapter):
        self.bot = adapter.bot
        self.add_handler(CommandHandler('rae', self.on_rae_command, command_description='Buscar definiciones en la Real Academia Española.'))
        self.add_handler(CallbackQueryHandler('rae:', self.on_button), priority=1)

    def setup_schedules(self, adapter):
        pass

    def html_parse(self, response):
        html_soup = BeautifulSoup(response.text, 'html.parser')
        r = {}
        if html_soup.find('noscript'):
            r['error'] = "noscript"
        else:
            error = html_soup.find('p')
            if error and "La palabra" in error.text:
                options = []
                for l in html_soup.find_all('li'):
                    t = {}
                    t['word'] = l.a.text
                    t['href'] = l.a['href']
                    options.append(t)
                r['options'] = options
            else:
                word = html_soup.find('header', class_='f')
                if word:
                    r['word'] = word.text   
                    abbr = html_soup.find('p', class_='n2')
                    if abbr:
                        r['abbr'] = abbr.text.replace("*","")
        
                    definitions = []
                    for d in html_soup.find_all('p', class_="j"):
                        definitions.append(d.text)
                    r['definitions'] = definitions
                else:
                    options = []
                    for l in html_soup.find_all('li'):
                        t = {}
                        t['word'] = l.a.text
                        t['href'] = l.a['href']
                        options.append(t)
                    r['options'] = options
        return r    

    def html_value(self, response):
        r = {}       
        for t in response.text.split("\n"):
            if "var c = " in t:
                r['c'] = t.split("=")[1].strip()
        
            if "var slt = " in t:
                r['slt'] = t.split("=")[1].replace("\"","").strip()
        
            if "var s1 = " in t:
                r['s1'] = t.split("=")[1].replace("\'","").strip()

            if "var s2 = " in t:
                r['s2'] = t.split("=")[1].replace("\'","").strip()

            if "var table = " in t:
                r['table'] = t.split("var table =")[1].replace("\"","").replace(";","").strip()
        
            if "document.forms[0].elements[1].value=" in t:
                r['session'] = t.split("\"")[1]    
        return r

    def html_challenge(self, data):
        table = data['table']
        c = data['c']
        slt = data['slt']
        s1 = data['s1']
        s2 = data['s2']
        n = 4

        start = ord(s1)
        end = ord(s2)
        m = ((end - start) + 1) ** n
         
        arr = list(s1 * 4)
         
        for i in range(m):
                for j in range(n-1, -1, -1):
                        t = ord(arr[j])
                        t = t + 1
                        arr[j] = chr(t)
         
                        if ord(arr[j]) <= end:
                                break
                        else:
                                arr[j] = s1

                chlg = ''.join(arr)
                str1 = chlg + slt
                crc = 0
                crc = crc ^ (-1)
         
                for k in range(len(str1)):
                        v = ((crc ^ ord(str1[k])) & 0x000000ff) * 9
                        crc = ctypes.c_int((crc >> 8 ^ int(table[v:v+8], 16)) ^ 0).value
         
                crc = abs(crc ^ (-1))
         
                if crc == int(c):
                    return chlg
        return ""

    def http(self, word="", url=""):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
            "Connection": "close"   
        }
        
        with requests.Session() as s:
            if not url:
                payload = (
                    ("w" , word),
                    ("m" , "form")
                )
                url = "{}/srv/search/".format(self.config.get('base_url'))
                response = s.get(url, params=payload, headers=headers)
            else:
                response = s.get(url, headers=headers)

            r = self.html_parse(response)

            if 'error' in r:
                data = self.html_value(response)
                chlg = self.html_challenge(data)

                session = data['session'] + chlg + ":" + data['slt'] + ":" + data['c'];

                params = (
                    ("TS017111a7_id" , "3"),
                    ("TS017111a7_cr" , session),
                    ("TS017111a7_76" , "0"),
                    ("TS017111a7_86" , "0"),
                    ("TS017111a7_md" , "1"),
                    ("TS017111a7_rf" , "0"),
                    ("TS017111a7_ct" , "0"),
                    ("TS017111a7_pd" , "0")
                )

                headers['Origin'] = "http://dle.rae.es"
                headers['Cache-Control'] = "max-age=0"

                if word:
                    url = "{}/srv/search/?w={}&m=form".format(self.config.get('base_url'), word)
                    headers['Referer'] = "{}/srv/search/".format(self.config.get('base_url'))
                    response = s.post(url, data=params, headers=headers)
                else:
                    headers['Referer'] = url
                    response = s.post(url, data=params, headers=headers)

                r = self.html_parse(response)

            return r

    def make_msg(self, rae):
        msg = ""

        if 'error' in rae:
            return "Un error ha ocurrido"

        if 'word' in rae:
                msg = "📖 *{}*\n".format(rae['word'].strip("."))
            
        if 'abbr' in rae:
            msg +=  "{}\n".format(rae['abbr'])

        if 'definitions' in rae:
            msg += "\n".join(rae['definitions'][:3])

        return msg

    def on_rae_command(self, update, *args, **kwargs):
        message = get_message(update)
        msg = ""
        reply_markup = ""

        try:
            cmd_args = message.text.split(" ")
            if len(cmd_args) > 1:
                word = cmd_args[1]
                rae = self.http(word=word)
                if 'options' in rae:
                    options = []
                    
                    for o in rae['options']:
                        d = "rae:{}".format(o['href'])
                        options.append([InlineKeyboardButton(text=o['word'].strip("."), callback_data=d)])
                    
                    if len(options) > 0:
                        reply_markup = InlineKeyboardMarkup(options)
                    else:
                        msg = "❌ No se encontro una relación"
                        reply_markup = ""
                else:
                    msg = self.make_msg(rae)
            else:
                msg = "‼️ Utiliza: /rae <palabra>"
        except Exception as err:
            log.error("Rae error: {}".format(err))
            msg = "❌ Un error ha ocurrido"

        if reply_markup:
            self.adapter.bot.sendMessage(chat_id=message.chat_id, text="📚 Quiso decir:", reply_markup=reply_markup)
        else:
            self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
        
    def on_button(self, update):
        query = update.callback_query
        data = query.data.split(":")
        try:
            self.bot.deleteMessage(chat_id=query.message.chat_id, message_id=query.message.message_id)
        except:
            query.message.edit_reply_markup(reply_markup=None)

        msg = ""

        try:
            url = "{}/srv/{}".format(self.config.get('base_url'), data[1])
            rae = self.http(url=url)
            msg = self.make_msg(rae)
        except Exception as err:
            log.error("Rae button error: {}".format(err))
            msg = "❌ Un error ha ocurrido"

        self.adapter.bot.sendMessage(chat_id=query.message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
          
