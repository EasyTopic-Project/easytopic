from flask import Flask, request, flash, redirect
import pika
import os
import json

from werkzeug.utils import secure_filename
from tempfile import gettempdir
from files_ms_client import upload
from DAO.connection import Connection
# from files_ms_client.client import upload
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = gettempdir()

@app.route('/vad', methods=['POST'])
def vad():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and (file.filename.endswith('.mp3') or file.filename.endswith('.wav')):
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=os.environ['QUEUE_SERVER']))
            channel = connection.channel()
            channel.queue_declare(queue='vad', durable=True)

            file_url = upload(file.read(), buffer=True, mime=file.mimetype)['name']

            # DB
            db_conn = Connection()
            oid = db_conn.insert_jobs(
                type='vad', status='new', file=file.read())
            message = {'type': 'vad', 'status': 'new',
                       'oid': oid, 'file': file_url}
            channel.basic_publish(
                exchange='', routing_key='vad', body=json.dumps(message))
            connection.close()
            return 'Done'
        else:
            return 'Invalid file'


@app.route('/asr', methods=['POST'])
def asr():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and (file.filename.endswith('.mp3') or file.filename.endswith('.wav')):
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='asr')

            file_url = upload(file.read(), buffer=True, mime=file.mimetype)['name']

            # DB
            db_conn = Connection()
            oid = db_conn.insert_jobs(
                type='asr', status='new', file=file.read())
            message = {'type': 'asr', 'status': 'new',
                       'oid': oid, 'file': file_url}
            channel.basic_publish(
                exchange='', routing_key='asr', body=str(message))
            connection.close()
            return 'Done'
        else:
            flash('Invalid file')
            return redirect(request.url)


@app.route('/segmentation',  methods=['POST'])
def extract_audio():

    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and (file.filename.endswith('.mp4') or file.filename.endswith('.avi')):
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='audio_extractor', durable=True)

            print("XAXA:                ", os.getenv('FILES_URL', 'XORUMELOS'))
            file_url = upload(file.read(), buffer=True, mime=file.mimetype)['name']

            # DB
            db_conn = Connection()
            file_oid = db_conn.insert_doc_mongo(file.read())
            oid, project_id = db_conn.insert_jobs(
                type='audio_extractor', status='new', file=file_oid, file_name=file.filename)
            message = {'type': 'audio_extractor', 'status': 'new',
                       'oid': file_oid, 'project_id': project_id, 'file': file_url}
            channel.basic_publish(
                exchange='', routing_key='audio_extractor', body=json.dumps(message))
            connection.close()
            return {'project_id': project_id}
        else:
            flash('Invalid file')
            return redirect(request.url)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
