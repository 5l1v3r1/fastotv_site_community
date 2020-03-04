#!/usr/bin/env python3
import argparse
import os
import sys
from pymodm import connect

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pyfastocloud_models.subscriber.login.entry import SubscriberUser

PROJECT_NAME = 'create_provider'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=PROJECT_NAME, usage='%(prog)s [options]')
    parser.add_argument('--mongo_uri', help='MongoDB credentials', default='mongodb://localhost:27017/iptv')
    parser.add_argument('--email', help='Subscriber email')
    parser.add_argument('--first_name', help='First name')
    parser.add_argument('--last_name', help='Last name')
    parser.add_argument('--language', help='Language')
    parser.add_argument('--password', help='Subscriber password')
    parser.add_argument('--country', help='Subscriber country', default='US')

    argv = parser.parse_args()

    mongo = connect(argv.mongo_uri)
    if mongo:
        new_user = SubscriberUser.make_subscriber(email=argv.email.lower(), first_name=argv.first_name,
                                                  last_name=argv.last_name, password=argv.password,
                                                  country=argv.country, language=argv.language)
        new_user.status = SubscriberUser.Status.ACTIVE
        new_user.save()
