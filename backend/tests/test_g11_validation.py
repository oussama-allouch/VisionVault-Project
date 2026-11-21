"""Mathematical and HTTP regressions on isolated files and database."""

import io
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image as PILImage

from app import create_app
from app.cbir.feature_extractor import extract_features_with_details, extract_features
from app.cbir.indexer import FeatureIndex
from app.cbir.reweighting_type1 import compute_weights_type1, update_query_vector
from app.cbir.similarity import weighted_euclidean
from app.config import Config
from app.extensions import db
from app.models.search import FeedbackIteration
from app.models.user import User
from app.services.dataset_service import DatasetService


@pytest.fixture()
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(tmp_path / 'gallery.sqlite')
        DATASET_PATH = str(tmp_path / 'dataset')
        UPLOAD_FOLDER = str(tmp_path / 'uploads')
        THUMBNAIL_FOLDER = str(tmp_path / 'thumbnails')
        INDEX_FOLDER = str(tmp_path / 'index')
        DEMO_EMAIL = 'test@example.test'
        DEMO_PASSWORD = 'temporary-unit-password'
    result = create_app(TestConfig)
    with result.app_context():
        second = User(email='other@example.test', role='user')
        second.set_password(TestConfig.DEMO_PASSWORD)
        db.session.add(second)
        db.session.commit()
    return result


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email='test@example.test'):
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': 'temporary-unit-password'})
    assert response.status_code == 200
    return response.json


def auth(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def headers(client):
    return auth(login(client)['access_token'])


def png(color, size=(40, 30)):
    file = io.BytesIO()
    PILImage.new('RGB', size, color).save(file, 'PNG')
    file.seek(0)
    return file


def upload(client, headers, color, category_id=None):
    fields = {'file': (png(color), 'fixture.png')}
    if category_id is not None:
        fields['category_id'] = str(category_id)
    response = client.post('/api/v1/images', data=fields, headers=headers)
    assert response.status_code == 201, response.json
    return response.json


def test_constant_color_and_known_glcm(tmp_path):
    path = tmp_path / 'uniçode.png'
    path.write_bytes(png((255, 0, 0)).getvalue())
    d = extract_features_with_details(str(path))
    np.testing.assert_array_almost_equal(d['vector'], extract_features(str(path)), decimal=12)
    assert len(d['vector']) == 93 and np.isfinite(d['vector']).all()
    assert d['color_moments']['details']['H']['skewness'] == 0
    assert d['color_histogram']['h_hist'][0] == 1
    assert d['color_histogram']['s_hist'][-1] == 1
    assert d['dominant_colors']['colors'] == [{'rgb': [255, 0, 0], 'hex': '#FF0000', 'percentage': 1}]
    np.testing.assert_array_equal(d['dominant_colors']['feature_vector'][:4], [1, 0, 0, 1])
    np.testing.assert_array_equal(d['dominant_colors']['feature_vector'][4:], np.zeros(16))
    np.testing.assert_allclose(d['glcm']['features'], [0, 1, 1, 1, 0, 1])
    assert d['lbp']['histogram'].sum() == pytest.approx(1)


def test_type1_independent_expected_example():
    retrieved = [[0, 2], [2, 2], [4, 8]]
    relevant = [[0, 2], [2, 2]]
    expected = [(np.sqrt(8/3) + .0001) / 1.0001, (np.sqrt(8) + .0001) / .0001]
    weights, _ = compute_weights_type1(retrieved, relevant)
    np.testing.assert_allclose(weights, expected)
    np.testing.assert_array_equal(update_query_vector(relevant), [1, 2])
    assert weighted_euclidean([1, 2], [4, 8], weights) == pytest.approx(
        np.sqrt((9 * expected[0] + 36 * expected[1]) / sum(expected)))


@pytest.mark.parametrize('invalid', ([[np.nan, 0]], [[np.inf, 0]], [[1, 2, 3]], [], [1, 2]))
def test_type1_invalid_matrices(invalid):
    with pytest.raises(ValueError):
        compute_weights_type1([[0, 0]], invalid)


@pytest.mark.parametrize('weights', ([1], [0, 0], [-1, 1], [np.nan, 1]))
def test_invalid_distance_weights(weights):
    with pytest.raises(ValueError):
        weighted_euclidean([1, 2], [4, 8], weights)


def test_login_media_logout_and_admin(app, client, headers):
    assert client.get('/api/v1/images').status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': 'test@example.test', 'password': 'wrong'}).status_code == 401
    login_record = login(client)
    gallery_token = auth(login_record['access_token'])
    image = upload(client, gallery_token, (200, 101, 10))
    assert client.get(image['image_url']).status_code == 401
    assert client.get(image['thumbnail_url'], headers=gallery_token).status_code == 200
    assert client.get('/api/v1/images/static/images/missing', headers=gallery_token).status_code == 404
    other = auth(login(client, 'other@example.test')['access_token'])
    assert client.post('/api/v1/index/rebuild', headers=other).status_code == 403
    current = client.post('/api/v1/auth/refresh', headers=auth(login_record['refresh_token']))
    assert current.status_code == 200
    assert client.post('/api/v1/auth/logout', headers=gallery_token).status_code == 200
    assert client.get('/api/v1/auth/me', headers=auth(current.json['access_token'])).status_code == 401
    assert client.post('/api/v1/auth/refresh', headers=auth(login_record['refresh_token'])).status_code == 401


def test_gallery_hierarchy_zip_transform_and_index(app, client, headers):
    def post(url, **data):
        return client.post('/api/v1/' + url, json=data, headers=headers)
    parent = post('categories', name='Parent').json
    child = post('categories', name='Child', parent_id=parent['id']).json
    cycle = client.patch(f"/api/v1/categories/{parent['id']}", json={'parent_id': child['id']}, headers=headers)
    assert cycle.status_code == 400
    item = upload(client, headers, (10, 50, 120), child['id'])
    source = client.get(f"/api/v1/images/{item['id']}/download", headers=headers).data
    supplied = {'files': [(png((3, 8, 10)), 'same.png'), (png((13, 18, 10)), 'same.png')]}
    bulk = client.post('/api/v1/images/bulk-upload', data=supplied, headers=headers).json['uploads']
    assert [i['status'] for i in bulk] == [201, 201]
    bad = client.post('/api/v1/images', data={'file': (io.BytesIO(b'test'), 'bad.jpg')}, headers=headers)
    assert bad.status_code == 400
    url = f"images/{item['id']}"
    assert post(url + '/crop', x=39, y=0, width=2, height=1).status_code == 400
    crop = post(url + '/crop', x=5, y=5, width=12, height=10)
    assert (crop.status_code, crop.json['width'], crop.json['height'], crop.json['is_indexed']) == (201, 12, 10, True)
    resized = post(url + '/resize', width=20, height=20, maintain_aspect=True)
    assert (resized.status_code, resized.json['width'], resized.json['height']) == (201, 20, 15)
    assert post(url + '/resize', width=60000).status_code == 400
    assert client.get('/api/v1/' + url + '/download', headers=headers).data == source
    batch = post('images/features/batch', ids=[item['id'], crop.json['id'], 10000])
    assert [i['status'] for i in batch.json['items']] == [200, 200, 404]
    assert all('lbp' in i['features'] for i in batch.json['items'][:2])
    ids = [member['result']['id'] for member in bulk]
    archive = post('images/bulk-download', ids=ids)
    with zipfile.ZipFile(io.BytesIO(archive.data)) as file:
        assert len(set(file.namelist())) == 2
    assert post('images/bulk-delete', ids=ids).json['deleted'] == 2
    assert client.delete('/api/v1/' + url, headers=headers).status_code == 200
    index = FeatureIndex(app.config['INDEX_FOLDER'])
    index.load()
    assert set(index.image_ids) == {crop.json['id'], resized.json['id']}
    np.testing.assert_allclose(index.get_features(crop.json['id']), index.normalizer.transform(index.get_raw_features(crop.json['id'])))
    assert client.delete(f"/api/v1/categories/{parent['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/categories/{child['id']}", headers=headers).json['parent_id'] is None


def test_production_feedback_matches_independent_calculation(app, client, headers):
    category = client.post('/api/v1/categories', json={'name': 'Query'}, headers=headers).json
    imgs = [upload(client, headers, (c, 255-c, c//2), category['id'] if n < 3 else None)
            for n, c in enumerate([20, 60, 100, 180, 240])]
    q = imgs[0]['id']
    result = client.post('/api/v1/cbir/search', json={'query_image_id': q, 'num_results': 10}, headers=headers)
    assert result.status_code == 200, result.json
    first = result.json
    assert first['precision_at_k'] == .5 and first['recall_at_k'] == 1
    ids = [r['image_id'] for r in first['results']]
    assert q not in ids
    session_id = first['session_id']
    other = auth(login(client, 'other@example.test')['access_token'])
    for suffix in ('', '/history'):
        assert client.get(f'/api/v1/cbir/sessions/{session_id}{suffix}', headers=other).status_code == 404
    assert client.get('/api/v1/analytics/evaluation', headers=other).json['total_evaluated_sessions'] == 0
    endpoint = '/api/v1/cbir/feedback'
    data = {'session_id': session_id, 'iteration': 1, 'num_results': 4}
    for positive, negative in [(ids[:1] * 2, []), (ids[:1], ids[:1]), ([q], []), ([True], []),
                               ([], []), (ids[:1], [q]), (ids[:1], ['not-an-id'])]:
        response = client.post(endpoint, headers=headers, json={**data, 'relevant_ids': positive, 'non_relevant_ids': negative})
        assert response.status_code == 400, response.json
    response = client.post(endpoint, json={**data, 'relevant_ids': ids[:2], 'non_relevant_ids': ids[2:3]}, headers=headers)
    assert response.status_code == 200, response.json
    persisted = FeatureIndex(app.config['INDEX_FOLDER'])
    persisted.load()
    vectors = np.array([persisted.get_features(i) for i in ids])
    weights = (.0001 + vectors.std(axis=0)) / (.0001 + vectors[:2].std(axis=0))
    centroid = vectors[:2].mean(axis=0)
    np.testing.assert_allclose(response.json['weights'], weights)
    with app.app_context():
        feedback = FeedbackIteration.query.filter_by(session_id=session_id, iteration_number=1).one()
        np.testing.assert_allclose(feedback.query_vector, centroid)
    distances = dict(zip(ids, np.sqrt(((vectors - centroid) ** 2 * weights).sum(axis=1) / weights.sum())))
    expected = sorted(ids, key=lambda i: (distances[i], i))
    assert [r['image_id'] for r in response.json['results']] == expected
    np.testing.assert_allclose([r['distance'] for r in response.json['results']], [distances[i] for i in expected], atol=1e-6)
    assert client.post(endpoint, json={**data, 'relevant_ids': ids[:1]}, headers=headers).status_code == 409
    second = client.post(endpoint, json={**data, 'iteration': 2, 'relevant_ids': ids}, headers=headers)
    assert second.status_code == 200
    np.testing.assert_array_equal(second.json['weights'], np.ones(93))
    assert q not in [r['image_id'] for r in second.json['results']]


def test_dataset_import_counts_duplicates_and_unreadables(app):
    root = Path(app.config['DATASET_PATH'])
    root.mkdir()
    actual = PILImage.new('RGB', (16, 18), (40, 90, 220))
    actual.save(root / '0_1.jpg')
    (root / '0_2.jpg').write_bytes((root / '0_1.jpg').read_bytes())
    (root / '1_501.jpg').write_bytes(b'bad data')
    with app.app_context():
        stats = DatasetService.import_dataset(root)
        repeat = DatasetService.import_dataset(root)
    assert stats['observed_categories'] == {'Classe 00': 2, 'Classe 01': 1}
    assert stats['images_imported'] == 1 and repeat['images_imported'] == 0
    assert stats['duplicate_files'] == ['0_2.jpg']
    assert stats['unreadable_files'] == ['1_501.jpg']
    assert stats['formats'] == {'JPEG': 2}
