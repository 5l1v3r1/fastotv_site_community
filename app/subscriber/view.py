import json

from flask_classy import FlaskView, route
from flask import render_template, redirect, url_for, request, jsonify, Response
from flask_login import login_required, current_user

from bson.objectid import ObjectId
from pyfastocloud_models.subscriber.entry import Device
from app.common.service.forms import UploadM3uForm
from pyfastocloud_models.utils.m3u_parser import M3uParser
from pyfastocloud_models.utils.utils import is_valid_http_url
from pyfastocloud_models.stream.entry import ProxyStream, ProxyVodStream
from app.common.stream.forms import ProxyStreamForm, ProxyVodStreamForm
import pyfastocloud_models.constants as constants
from app import app


# routes
class SubscriberView(FlaskView):
    route_base = "/subscriber"

    @login_required
    def profile(self):
        return render_template('subscriber/profile.html')

    @login_required
    def channels(self):
        streams = []

        def for_subscribers_stream(stream):
            if not stream:
                return False
            if not stream.visible:
                return False
            stream_type = stream.get_type()
            return stream_type == constants.StreamType.PROXY or stream_type == constants.StreamType.VOD_PROXY or \
                   stream_type == constants.StreamType.RELAY or stream_type == constants.StreamType.ENCODE or \
                   stream_type == constants.StreamType.TIMESHIFT_PLAYER or \
                   stream_type == constants.StreamType.CATCHUP or stream_type == constants.StreamType.VOD_RELAY or \
                   stream_type == constants.StreamType.VOD_ENCODE or stream_type == constants.StreamType.COD_RELAY or \
                   stream_type == constants.StreamType.COD_ENCODE

        for serv in current_user.servers:
            for stream in serv.streams:
                if for_subscribers_stream(stream):
                    streams.append(stream.to_dict())

        selected_streams = []
        for stream in current_user.streams:
            front = stream.to_front_dict()
            selected_streams.append(front)
        return render_template('subscriber/channels.html', streams=streams, selected_streams=selected_streams)

    @login_required
    def my_channels(self):
        form = UploadM3uForm(type=constants.StreamType.PROXY)
        form.type.choices = [(constants.StreamType.PROXY, 'Proxy Stream'),
                             (constants.StreamType.VOD_PROXY, 'Proxy Vod')]
        streams = []
        for stream in current_user.own_streams():
            streams.append(stream.to_dict())

        return render_template('subscriber/my_channels.html', form=form, streams=streams)

    @login_required
    @route('/upload_files', methods=['POST'])
    def upload_files(self):
        form = UploadM3uForm()
        if form.validate_on_submit():
            files = request.files.getlist("files")
            for file in files:
                m3u_parser = M3uParser()
                m3u_parser.load_content(file.read().decode('utf-8'))
                m3u_parser.parse()

                default_logo_path = constants.DEFAULT_STREAM_PREVIEW_ICON_URL
                for file in m3u_parser.files:
                    if form.type.data == constants.StreamType.PROXY:
                        stream = ProxyStream.make_stream(None)
                    else:
                        stream = ProxyVodStream.make_stream(None)

                    input_url = file['link']
                    stream.output.urls[0].uri = input_url

                    stream.tvg_logo = default_logo_path

                    title = file['title']
                    if len(title) < constants.MAX_STREAM_NAME_LENGTH:
                        stream.name = title

                    tvg_id = file['tvg-id']
                    if len(tvg_id) < constants.MAX_STREAM_TVG_ID_LENGTH:
                        stream.tvg_id = tvg_id

                    tvg_name = file['tvg-name']
                    if len(tvg_name) < constants.MAX_STREAM_NAME_LENGTH:
                        stream.tvg_name = tvg_name

                    tvg_group = file['tvg-group']
                    if len(tvg_group) < constants.MAX_STREAM_GROUP_TITLE_LENGTH:
                        stream.group = tvg_group

                    tvg_logo = file['tvg-logo']
                    if len(tvg_logo) < constants.MAX_URL_LENGTH:
                        if is_valid_http_url(tvg_logo, timeout=0.1):
                            stream.tvg_logo = tvg_logo
                    stream.save()
                    current_user.add_own_stream(stream)

        return redirect(url_for('SubscriberView:my_channels'))

    @route('/remove_own_stream', methods=['POST'])
    @login_required
    def remove_own_stream(self):
        data = request.get_json()
        sids = data.get('sids', None)
        if not sids:
            return jsonify(status='failed', error='Invalid input(country required)'), 400

        for sid in sids:
            current_user.remove_own_stream_by_id(ObjectId(sid))
        return jsonify(status='ok'), 200

    @login_required
    def remove_all_own_streams(self):
        current_user.remove_all_own_streams()
        return jsonify(status='ok'), 200

    @login_required
    @route('/add/own/proxy_stream', methods=['GET', 'POST'])
    def add_own_proxy_stream(self):
        stream = ProxyStream.make_stream(None)
        form = ProxyStreamForm(obj=stream)
        form.price.validators = []
        if request.method == 'POST' and form.validate_on_submit():
            new_entry = form.make_entry()
            new_entry.save()
            current_user.add_own_stream(new_entry)
            return jsonify(status='ok'), 200

        return render_template('stream/proxy/add.html', form=form)

    @login_required
    @route('/add/own/proxy_vod', methods=['GET', 'POST'])
    def add_own_proxy_vod(self):
        stream = ProxyVodStream.make_stream(None)
        form = ProxyVodStreamForm(obj=stream)
        form.price.validators = []
        if request.method == 'POST' and form.validate_on_submit():
            new_entry = form.make_entry()
            new_entry.save()
            current_user.add_own_stream(new_entry)
            return jsonify(status='ok'), 200

        return render_template('stream/vod_proxy/add.html', form=form)

    @login_required
    @route('/edit/own/<sid>', methods=['GET', 'POST'])
    def edit(self, sid):
        stream = current_user.find_own_stream(ObjectId(sid))
        if not stream:
            return jsonify(status='failed'), 404

        if stream.get_type() == constants.StreamType.PROXY:
            form = ProxyStreamForm(obj=stream)
        else:
            form = ProxyVodStreamForm(obj=stream)

        form.price.validators = []
        if request.method == 'POST' and form.validate_on_submit():
            stream = form.update_entry(stream)
            stream.save()
            return jsonify(status='ok'), 200

        return render_template('stream/proxy/edit.html', form=form)

    @route('/apply_channels', methods=['POST'])
    @login_required
    def apply_channels(self):
        current_user.streams = []
        json_str = request.form['apply_channels_official_ids']
        if json_str:
            for sid in json.loads(json_str):
                oid = ObjectId(sid)
                current_user.add_official_stream_by_id(oid)
        current_user.save()
        return redirect(url_for('SubscriberView:channels'))

    @login_required
    def devices(self):
        return render_template('subscriber/devices.html')

    @login_required
    def downloads(self):
        return render_template('subscriber/downloads.html',
                               name=app.config['PUBLIC_CONFIG']['player']['name'],
                               name_lowercase=app.config['PUBLIC_CONFIG']['player']['name_lowercase'],
                               version=app.config['PUBLIC_CONFIG']['player']['version'])

    @route('/add_device', methods=['POST'])
    @login_required
    def add_device(self):
        device = Device(name=request.form['name'])
        current_user.add_device(device)
        return render_template('subscriber/devices.html')

    @route('/remove_device/<did>', methods=['POST'])
    @login_required
    def remove_device(self, did):
        current_user.remove_device(ObjectId(did))
        return render_template('subscriber/devices.html')

    @login_required
    @route('/playlist/<did>/master.m3u', methods=['GET'])
    def playlist(self, did):
        lb_server_host_and_port = app.config['SUBSCRIBERS_PORTAL_HTTP_SERVER']
        playlist = current_user.generate_playlist(did, lb_server_host_and_port)
        return Response(playlist, mimetype='application/x-mpequrl'), 200

    @login_required
    def build_installer_request(self):
        return render_template('subscriber/profile.html')

    @login_required
    def logout(self):
        current_user.logout()
        return redirect(url_for('HomeView:index'))

    @login_required
    def remove(self):
        current_user.delete()
        return redirect(url_for('HomeView:index'))
