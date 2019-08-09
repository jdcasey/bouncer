#!/usr/bin/env python3

import tornado.ioloop as loop
import tornado.web as web
from os import environ
from ruamel.yaml import YAML
import datetime
import re

BOUNCER_CONFIG = 'BOUNCER_CONFIG'
URL = 'url'
VARS = 'vars'
FROM = 'from'
TO = 'to'
DEFAULT = 'default'

def decode_default(val, args):
	return val

def decode_date_epoch(val, args):
	if 'now' in val:
		parts = val.split('-')
		if len(parts) == 1:
			return datetime.datetime.now()
		elif len(parts) > 1:
			return datetime.datetime.now() - datetime.timedelta(hours=int(parts[1][:-1]))
	elif isnumeric(val) is True:
		return datetime.datetime.fromtimestamp(int(val))

	return datetime.datetime.now()


def decode_regex(val, args):
	match = re.compile(args[0]).match(val)
	if match is None:
		return ''
	else:
		group = int(args[1])
		return match.group(group)

def encode_default(val, args):
	return val

def encode_iso8601(val, args):
	return val.isoformat()[:-3]

def encode_strformat(val, args):
	return args[0].format(val=val)


IN_FORMATS = {
	DEFAULT: decode_default,
	'epoch': decode_date_epoch,
	'regex': decode_regex
}

OUT_FORMATS = {
	DEFAULT: encode_default,
	'iso8601': encode_iso8601,
	'strformat': encode_strformat
}

class MainHandler(web.RequestHandler):
	def initialize(self, mapping):
		self.mapping = mapping

	def get(self):
		bounce = self.request.path[1:].split('/')[0]
		
		target = self.mapping.get(bounce)
		print(f"Target of: '{bounce}' is: '{target}'")
		if target is None:
			self.set_status(404, 'Target URL not found')
			return

		target_url_fmt = target[URL]
		target_vars = {}
		for key,formats in target[VARS].items():
			print(f"Processing var: '{key}'")
			inval = self.get_query_argument(key)
			print(f"Input value: '{inval}'")

			infmt = formats[FROM].split('|')
			inargs = infmt[1:] if len(infmt) > 1 else []
			interval = IN_FORMATS.get(infmt[0], IN_FORMATS[DEFAULT])(inval, inargs)
			print(f"Decoded value: '{interval}'")

			outfmt = formats[TO].split('|')
			outargs = outfmt[1:] if len(outfmt) > 1 else []
			target_vars[key] = OUT_FORMATS.get(outfmt[0], OUT_FORMATS[DEFAULT])(interval, outargs)
			print(f"Output value: '{target_vars[key]}'")

		print(target_vars)
		target_url = target_url_fmt.format(**target_vars)
		print(target_url)
		# self.redirect(target_url)


def make_app():
	config = environ.get(BOUNCER_CONFIG)
	if config is None:
		raise Exception(f"Cannot find YAML config under {BOUNCER_CONFIG}")

	mapping = {}
	with open(config) as f:
		yaml = YAML(typ='safe')
		mapping = yaml.load(f)
	print(mapping)

	return web.Application([
		(r"/.*", MainHandler, {'mapping': mapping})
	])

if __name__ == '__main__':
	app = make_app()
	app.listen(8888)
	print("Listening on port 8888")
	loop.IOLoop.current().start()
