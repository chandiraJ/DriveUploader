import io
import os
import sys

import flask
from flask import Flask, flash, request, redirect, url_for, render_template
import httplib2
from apiclient import discovery
from apiclient.http import MediaIoBaseDownload, MediaFileUpload
# import request
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from werkzeug.utils import secure_filename
app = flask.Flask(__name__,template_folder='templates')
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

UPLOAD_FOLDER = 'files'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'jpg','jpeg','png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

@app.route('/')
def index():
    credentials = get_credentials()
    if credentials == False:
        return flask.redirect(flask.url_for('oauth2callback'))
    elif credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        print('now calling fetch')
        all_files = fetch("'root' in parents and (mimeType = 'application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.file' or mimeType='application/vnd.google-apps.folder') ",
                          sort='modifiedTime desc')
        s = ""
        for file in all_files:
            s += "%s | " % (file['name'])
            #download_file(file['id'], file['name'])

        return render_template('interface.html',data=s)

@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets('client_id.json',
                                          scope='https://www.googleapis.com/auth/drive',
                                          redirect_uri=flask.url_for('oauth2callback',
                                                                     _external=True))  # access drive api using developer credentials
    flow.params['include_granted_scopes'] = 'true'
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        open('credentials.json', 'w').write(credentials.to_json())  # write access token to credentials.json locally
        return flask.redirect(flask.url_for('index'))


def get_credentials():
    credential_path = 'credentials.json'

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        print("Credentials not found.")
        return False
    else:
        print("Credentials retrieved successfully.")
        return credentials


def fetch(query, sort='modifiedTime desc'):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    results = service.files().list(
        q=query, orderBy=sort, pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items


@app.route('/uploadfile', methods=['GET', 'POST'])
def upload():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file found')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = file.filename
            print(filename)
            os.chmod(UPLOAD_FOLDER, 0o777)
            os.access('files', os.W_OK)  # Check for write access
            os.access('files', os.R_OK)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filepath=os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file_metadata = {'name': filename}
            media = MediaFileUpload(filepath, mimetype='image/png')
            file = service.files().create(body=file_metadata,media_body=media,fields='id').execute()
            print('Uploads file ID: %s' % file.get('id'))

    return render_template('list.html')


if __name__ == '__main__':
    if os.path.exists('client_id.json') == False:
        print('Resource Server credentials (client_id.json) not found.')
        exit()
    import uuid

    app.secret_key = str(uuid.uuid4())
    app.run(debug=True,port=5000)