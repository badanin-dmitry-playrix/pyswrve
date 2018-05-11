# -*- coding: utf-8 -*-

import os.path
from datetime import datetime, timedelta
from configparser import SafeConfigParser

import requests

from .exceptions import SwrveApiException


class SwrveSession:

    # Default swrve KPI factors
    kpi_factors = {'dau', 'mau', 'dau_mau', 'new_users', 'dpu', 'conversion',
                   'dollar_revenue', 'currency_spent', 'currency_spent_dau',
                   'currency_purchased', 'currency_purchased_dau',
                   'currency_given', 'items_purchased', 'items_purchased_dau',
                   'session_count', 'avg_session_length', 'arpu_daily',
                   'arppu_daily', 'arpu_monthly', 'arppu_monthly',
                   'avg_playtime', 'day30_retention'}

    for i in (1, 3, 7):
        kpi_factors.add('day%s_reengagement' % i)
        kpi_factors.add('day%s_retention' % i)

    kpi_taxable = {'dollar_revenue', 'arpu_daily', 'arppu_daily',
                   'arpu_monthly', 'arppu_monthly'}
    period_lens = {'day': 1, 'week': 7, 'month': 30, 'year': 360}

    conf_path = os.path.join(os.path.expanduser('~'), '.pyswrve')
    __conf = SafeConfigParser()

    def __init__(self, api_key=None, personal_key=None, section=None,
                 conf_path=None):
        """ __init__

        :param api_key: [:class:`str`] API Key from Swrve Dashboard -
            Setup -  Integration Settings - App Information
        :param personal_key: [:class:`str`] Your personal key from
            Swrve Dashboard Setup -  Integration Settings
        :param section: [:class:`str`] section in pyswrve config, you
            are able to store keys for different projects in different
            config sections
        :param conf_path: [:class:`str`] arg overrides default path to
            config file with entered
        """

        if section is None:
            section = 'defaults'
        self.section = section

        if not api_key or not personal_key:
            if conf_path is not None:
                self.con_path = conf_path

            self.__conf.read(self.conf_path)
            api_key = self.__conf.get(section, 'api_key')
            personal_key = self.__conf.get(section, 'personal_key')

        self._params = {
            'api_key': api_key,
            'personal_key': personal_key
        }

    def save_config(self):
        """ Save params to config file """

        for key in self._params:
            val = self._params[key]
            self.__conf.set(self.section, key, val)

        with open(self.conf_path, 'w') as f:
            self.__conf.write(f)

    def set_param(self, key, val):
        self._params[key] = val

    def set_dates(self, start=None, stop=None, period=None, period_len=None):
        """ Set start and stop or history params

        :param start: period's first date
        :type start: datetime, str
        :param stop: period's last date
        :type stop: datetime, str
        :param period: [:class:`str`] day, week, month or year
        :period_len: [:class:`int`] count of days (weeks, etc) in period
        """

        if period:
            if period_len is None:
                period_len = 1
            stop = datetime.today()
            days = period_len * self.period_lens(period)
            start = stop - timedelta(days=days)

        for _date in (start, stop):
            if isinstance(_date, datetime):
                _date = _date.strftime('%Y-%m-%d')

        self.defaults['start'] = start
        self.defaults['stop'] = stop

    def send_api_request(self, url, params):
        """ Send GET request to Swrve Export API

        :param url: [:class:`str`] url for request
        :param params: [:class:`dict`] dictionary with request params
        :returns: [:class:`dict`] request results
        :raises SwrveApiException: if request status_code != 200
        """

        req = requests.get(url, params=params)
        if req.status_code != 200:
            error = None
            try:
                error['error'] = req.json()['error']
            except ValueError:
                pass
            raise SwrveApiException(error, req.status_code, params, url)

        return req.json()

    def get_kpi(self, kpi, with_date=True, currency=None, multiplier=None):
        """ Request the kpi stats

        :param kpi: [:class:`str`] the kpi's name, one from
            `SwrveSession.kpi_factors`
        :param with_date: [`bool`] by default swrve return every element
            as [['D-2015-01-31', 126.0], ['D-2015-01-31', 116.0]] so
            the result is a list of lists, if `with_date` setted to `True`
            the original result is modifing to list of values like
            [126.0, 116.0]
        :param currency: [:class:`str`] in-project currency, used for kpis
            like currency_given
        :param multiplier: [:class:`float`] revenue multiplier like in Swrve
            Dashboard - Setup - Report Settings - Reporting Revenue,
            it applies to revenue, arpu and arppu
        :return: [:class:`list`] a list of lists with dates and values or
            a list of values
        """

        # Request url
        url = 'https://dashboard.swrve.com/api/1/exporter/kpi/%s.json' % kpi
        params = self._params.copy()
        if currency:
            params['currency'] = currency

        results = self.send_api_request(url, params)
        data = results[0]['data']

        if multiplier is not None and kpi in self.kpi_taxable:
            data = [[i[0], i[1]*multiplier] for i in data]

        if not with_date:
            data = [i[1] for i in data]

        return data

    def get_kpi_dau(self, factor, with_date=True, currency=None, params=None,
                    tax=None):
        """" Request data for KPI factor / DAU (per one user)

        :rtype: :class:`list`
        """

        # Request url
        url = 'https://dashboard.swrve.com/api/1/exporter/kpi/%s.json' % factor
        params = params or dict(self.defaults)  # request params
        if currency:
            params['currency'] = currency  # cash, coins, etc...

        dau = self.get_kpi('dau', False, currency, params)
        if not dau:  # dau will be None if request was failed with error
            return   # because error already was printed just return
        req = requests.get(url, params=params).json()

        fdata = req[0]['data']  # factor data
        data = []
        if not with_date:  # without date
            for i in range(len(dau)):
                # Check does dau[i] > 0 for ZeroDivisionError fix
                if dau[i]:
                    # Substract tax from value
                    if tax and (factor in self.kpi_taxable):
                        val = round((fdata[i][1] / dau[i]) * (1 - tax), 4)
                    else:  # no substraction
                        val = round(fdata[i][1] / dau[i], 4)
                else:
                    val = 0
                data.append(val)
        else:  # with date
            for i in range(len(dau)):
                if dau[i]:
                    if tax and (factor in self.kpi_taxable):
                        if fdata[i][1]:
                            fdata[i][1] = round((fdata[i][1] / dau[i])*(1-tax),
                                                4)
                    else:
                        fdata[i][1] = round(fdata[i][1] / dau[i], 4)
                else:
                    fdata[i][1] = 0
            data = fdata

        return data

    def get_few_kpi(self, factor_lst, with_date=True, per_user=False,
                    currency=None, params=None, tax=None):
        """ Request data for few different KPI factors

        :rtype: :class:`list`
        """

        params = params or dict(self.defaults)  # request params
        if currency:
            params['currency'] = currency  # cash, coins, etc...

        if per_user:
            get_func = self.get_kpi_dau
        else:
            get_func = self.get_kpi

        count_index = 0
        results = []
        for factor in factor_lst:
            if count_index == 0:

                if with_date:
                    results = get_func(factor, tax=tax)
                else:
                    results = [[i] for i in get_func(factor, False, tax=tax)]
                count_index += 1

            else:  # > 0
                data = get_func(factor, False, tax=tax)
                for i in range(len(data)):
                    results[i] += [data[i]]

        return results

    def get_evt_lst(self, params=None):
        """
        Request list with all events from swrve

        :rtype: :class:`list`
        """

        # Request url
        url = 'https://dashboard.swrve.com/api/1/exporter/event/list'
        params = params or dict(self.defaults)  # request params

        req = requests.get(url, params=params).json()  # do request
        # Request errors
        if isinstance(req, dict):
            if 'error' in req.keys():
                print('Error: %s' % req['error'])
                return

        return req

    def get_payload_lst(self, ename=None, params=None):
        """
        Request payloads list for event

        :rtype: :class:`list`
        """

        # Request url
        url = 'https://dashboard.swrve.com/api/1/exporter/event/payloads'
        params = params or dict(self.defaults)  # request params
        if ename:
            params['name'] = ename

        req = requests.get(url, params=params).json()  # do request
        # Request errors
        if isinstance(req, dict):
            if 'error' in req.keys():
                print('Error: %s' % req['error'])
                return

        return req

    def get_evt_stat(self, ename=None, payload=None, payload_val=None,
                     payload_sum=None, with_date=True, per_user=False,
                     params=None):
        """ Request events triggering count with(out) payload key.
        If with payload, keys are payload's values, else key is an event name.

        :rtype: :class:`dict`
        """

        if (payload_val or payload_sum) and not payload:
            print('\
If you use payload value or sum then you need to set payload too')
            return

        params = params or dict(self.defaults)  # request params
        if ename:
            params['name'] = ename
        if payload:
            params['payload_key'] = payload

        if payload:
            url = 'https://dashboard.swrve.com/api/1/exporter/event/payload'
        else:
            url = 'https://dashboard.swrve.com/api/1/exporter/event/count'

        req = requests.get(url, params=params).json()  # do request
        # Request errors
        if isinstance(req, dict):
            if 'error' in req.keys():
                print('Error: %s' % req['error'])
                return

        data = {}
        if payload and payload_val:
            payload_val = str(payload_val)
            for d in req:
                if d['payload_value'] == payload_val:
                    data[payload_val] = d['data']
                    break

        elif payload:  # with payload
            for d in req:
                if with_date:  # key is a payload value
                    data[d['payload_value']] = d['data']
                else:
                    data[d['payload_value']] = [i[1] for i in d['data']]

        else:  # without payload key is an event name
            if not with_date:
                data[req[0]['name']] = [i[1] for i in req[0]['data']]
            else:
                data[req[0]['name']] = req[0]['data']

            if per_user:  # calc for one user
                dau = self.get_kpi('dau', False, params=params)
                key = list(data.keys())[0]  # one element => first key
                for i in range(len(dau)):
                    if not with_date:
                        # Check does dau[i] > 0 for ZeroDivisionError fix
                        if dau[i]:
                            data[key][i] = round(data[key][i] / dau[i], 4)
                        else:
                            data[key][i] = 0
                    else:
                        if dau[i]:
                            data[key][i][1] = round(
                                data[key][i][1] / dau[i], 4
                            )
                        else:
                            data[key][i][1] = 0

        # Aggregate payload values
        if payload and payload_sum:
            for key in data:
                val = 0
                if not with_date:
                    for i in data[key]:
                        val += i
                else:
                    for i in data[key]:
                        val += i[1]

                data[key] = val

        return data

    def get_item_sales(self, item=None, tag=None, currency=None, revenue=True,
                       with_date=True, per_user=False, params=None):
        """
        Request count of item sales or revenue from items sales

        :rtype: :class:`dict`
        """

        params = params or dict(self.defaults)  # request params
        if item:
            params['uid'] = item
        if tag:
            params['tag'] = tag
        if currency:
            params['currency'] = currency

        if revenue:
            url = 'https://dashboard.swrve.com/api/1/exporter/item/revenue'
        else:
            url = 'https://dashboard.swrve.com/api/1/exporter/item/sales'

        req = requests.get(url, params=params).json()  # do request
        # Request errors
        if isinstance(req, dict):
            if 'error' in req.keys():
                print('Error: %s' % req['error'])
                return

        data = {}
        for d in req:
            # Key for data dict 'item name - currency'
            k = '%s - %s' % (d['name'], d['currency'])
            if not with_date:
                data[k] = [i[1] for i in d['data']]
            else:
                data[k] = d['data']

        if per_user:  # calc for one user
            dau = self.get_kpi('dau', False, params=params)

            for key in data.keys():
                for i in range(len(dau)):
                    if not with_date:
                        # Check does dau[i] > 0 for ZeroDivisionError fix
                        if dau[i]:
                            data[key][i] = round(data[key][i] / dau[i], 4)
                        else:
                            data[key][i] = 0
                    else:
                        if dau[i]:
                            data[key][i][1] = round(
                                data[key][i][1] / dau[i], 4
                            )
                        else:
                            data[key][i][1] = 0

        return data

    def get_segment_lst(self, params=None):
        """ Get List of all segments

        :rtype: :class:`list`
        """

        # Request url
        url = 'https://dashboard.swrve.com/api/1/exporter/segment/list'
        params = params or dict(self.defaults)  # request params

        req = requests.get(url, params=params).json()  # do request
        # Request errors
        if isinstance(req, dict):
            if 'error' in req.keys():
                print('Error: %s' % req['error'])
                return

        return req
