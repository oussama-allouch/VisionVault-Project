"""Browser acceptance path. Run against a disposable full GHIM-10K clone."""

import json
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import pytest

BASE = os.environ.get('VV_E2E_URL')
pytestmark = pytest.mark.skipif(not BASE, reason='VV_E2E_URL désactivé. Utiliser une copie jetable du catalogue.')


def test_browser_full_workflow(tmp_path):
    from playwright.sync_api import sync_playwright, expect
    dataset = Path(os.environ['DATASET_PATH'])
    evidence = Path(os.environ.get('VV_EVIDENCE_DIR', tmp_path))
    evidence.mkdir(parents=True, exist_ok=True)
    samples = ['0_1.jpg', '0_2.jpg', '1_501.jpg']
    manifest = []
    page_errors, console_errors, network_errors = [], [], []
    with sync_playwright() as manager:
        browser = manager.chromium.launch(executable_path=os.environ.get('VV_BROWSER'), headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, accept_downloads=True,
                                      color_scheme='light', reduced_motion='reduce')
        page = context.new_page()
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        page.on('response', lambda r: network_errors.append((r.status, urlparse(r.url).path))
                if r.status >= 400 and '/api/v1/' in r.url else None)

        def capture(filename, feature, action, image=None):
            page.evaluate("""async () => {
                await document.fonts.ready;
                const visible = [...document.images].filter(el => {
                  const r = el.getBoundingClientRect();
                  return r.bottom > 0 && r.top < innerHeight && r.width && r.height;
                });
                await Promise.all(visible.map(async el => {
                  for (let k = 0; k < 80 && (!el.complete || !el.naturalWidth); k++)
                    await new Promise(r => setTimeout(r, 45));
                  if (!el.naturalWidth) throw Error('Image visible sans pixels: ' + el.alt);
                }));
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            }""")
            shot = evidence / f'{filename}.png'
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=shot, animations='disabled')
            manifest.append({'filename': f'{filename}.png', 'route': urlparse(page.url).path,
                             'feature': feature, 'interaction': action, 'dataset_id': image,
                             'date': os.environ.get('VV_CAPTURE_DATE'), 'test': 'E2E-G11'})

        def goto(path, heading):
            page.goto(BASE + path)
            expect(page.get_by_role('heading', name=heading, exact=True)).to_be_visible()

        def wait_api(path, method='POST'):
            return page.expect_response(lambda r: urlparse(r.url).path == '/api/v1/' + path
                                        and r.request.method == method)

        try:
            page.goto(BASE + '/gallery')
            expect(page).to_have_url(re.compile('/login$'))
            capture('application/01_connexion', 'Connexion', 'Accès protégé redirigé vers le formulaire vide')
            email = page.get_by_label('Email')
            password = page.get_by_label('Mot de passe')
            email.fill(os.environ['DEMO_EMAIL'])
            password.fill('invalid-test-password')
            page.get_by_role('button', name='Se connecter').click()
            expect(page.get_by_text('Email ou mot de passe invalide.')).to_be_visible()
            password.fill(os.environ['DEMO_PASSWORD'])
            page.get_by_role('button', name='Se connecter').click()
            expect(page).to_have_url(re.compile('/dashboard$'))
            expect(page.get_by_text(re.compile(r'9[\s, ]?998')).first).to_be_visible()
            capture('application/02_tableau', 'Tableau de bord', 'Connexion au catalogue GHIM-10K')
            goto('/gallery', "Galerie d'images")
            expect(page.get_by_role('button', name='Page suivante')).to_be_visible()
            capture('application/03_galerie', 'Galerie', 'Affichage de la première page avec miniatures')
            page.get_by_role('button', name='Page suivante').click()
            expect(page.get_by_text(re.compile(r'Page 2 /'))).to_be_visible()

            goto('/categories', 'Gestion des catégories')
            name = page.get_by_placeholder('Nouvelle catégorie...')
            name.fill('Démonstration G11')
            with wait_api('categories') as parent_response:
                page.get_by_role('button', name='Créer', exact=True).click()
            parent = parent_response.value.json()
            name.fill('Sélection GHIM')
            page.get_by_label('Catégorie parente').select_option(str(parent['id']))
            with wait_api('categories') as child_response:
                page.get_by_role('button', name='Créer', exact=True).click()
            child = child_response.value.json()
            page.get_by_role('button', name='Afficher Démonstration G11').click()
            page.get_by_role('button', name='Renommer Sélection GHIM').click()
            rename = page.get_by_label('Nouveau nom de Sélection GHIM')
            rename.fill('Photographies GHIM')
            rename.press('Enter')
            expect(page.get_by_role('button', name='Renommer Photographies GHIM')).to_be_visible()
            page.get_by_role('button', name='Renommer Photographies GHIM').scroll_into_view_if_needed()
            capture('application/04_categories', 'Hiérarchie', 'Création parent et enfant, puis renommage')

            goto('/upload', 'Téléverser des images')
            file_input = page.locator('input[type=file]')
            file_input.set_input_files(str(dataset / samples[0]))
            with wait_api('images') as single_response:
                page.get_by_role('button', name='Téléverser 1 fichier(s)').click()
            single = single_response.value.json()
            expect(page.get_by_role('heading', name='Résultats')).to_be_visible()
            assert single['is_indexed']
            file_input.set_input_files([str(dataset / n) for n in samples[1:]])
            page.get_by_label('Catégorie de destination').select_option(str(child['id']))
            with wait_api('images/bulk-upload') as bulk_response:
                page.get_by_role('button', name='Téléverser 2 fichier(s)').click()
            bulk = bulk_response.value.json()['uploads']
            assert all(row['status'] == 201 and row['result']['is_indexed'] for row in bulk)
            expect(page.get_by_text(samples[-1], exact=True)).to_be_visible()
            capture('application/05_televersement', 'Téléversement multiple', 'Import de deux photographies GHIM dans une catégorie enfant', samples[1:])

            goto('/gallery', "Galerie d'images")
            first, second = [row['result'] for row in bulk]
            page.get_by_role('img', name=single['filename'], exact=True).click()
            expect(page.get_by_role('heading', name=single['filename'])).to_be_visible()
            capture('application/06_detail', 'Détail', 'Ouverture d’un original et lecture des métadonnées', samples[0])
            with page.expect_download() as single_download:
                page.get_by_role('button', name='Télécharger l’original').click()
            assert Path(single_download.value.path()).read_bytes() == (dataset / samples[0]).read_bytes()
            with wait_api(f"images/{single['id']}/move"):
                page.get_by_label('Déplacer vers').select_option(str(child['id']))
            page.get_by_role('button', name='Fermer').click()
            page.get_by_role('checkbox', name=f"Sélectionner {first['filename']}").check(force=True)
            page.get_by_role('checkbox', name=f"Sélectionner {second['filename']}").check(force=True)
            capture('application/07_selection_zip', 'Sélection et téléchargement ZIP', 'Deux images sélectionnées dans la galerie', samples[1:])
            with page.expect_download() as zip_download:
                page.get_by_role('button', name='Télécharger ZIP').click()
            with zipfile.ZipFile(zip_download.value.path()) as archive:
                assert len(archive.namelist()) == 2
                assert set(archive.read(n) for n in archive.namelist()) == {(dataset / n).read_bytes() for n in samples[1:]}
            page.locator('select').first.select_option(str(child['id']))
            expect(page.get_by_text('3 images au total')).to_be_visible()

            goto(f"/editor/{single['id']}", "Éditeur d'images")
            source = page.get_by_test_id('crop-surface')
            source.locator('img').evaluate("(im) => im.decode()")
            page.get_by_role('button', name='Recadrer').click()
            rect = source.bounding_box()
            assert rect
            page.mouse.move(rect['x'] + rect['width'] * .23, rect['y'] + rect['height'] * .18)
            page.mouse.down()
            page.mouse.move(rect['x'] + rect['width'] * .75, rect['y'] + rect['height'] * .74, steps=14)
            page.mouse.up()
            expect(page.get_by_test_id('crop-selection')).to_be_visible()
            capture('transformations/08_recadrage', 'Recadrage interactif', 'Sélection à la souris sur la photo originale', samples[0])
            with wait_api(f"images/{single['id']}/crop") as cropped_response:
                page.get_by_role('button', name='Appliquer').click()
            cropped = cropped_response.value.json()
            assert cropped['parent_image_id'] == single['id'] and cropped['is_indexed']
            expect(page.get_by_role('img', name='result')).to_be_visible()
            capture('transformations/09_resultat_recadre', 'Image recadrée', 'Affichage du nouveau fichier après recadrage', samples[0])
            page.get_by_role('button', name='Redimensionner').click()
            page.get_by_label('Largeur').fill('220')
            page.get_by_label('Hauteur').fill('220')
            with wait_api(f"images/{single['id']}/resize") as resized_response:
                page.get_by_role('button', name='Appliquer').click()
            resized = resized_response.value.json()
            assert max(resized['width'], resized['height']) == 220
            assert abs(resized['width'] / resized['height'] - single['width'] / single['height']) < .015
            capture('transformations/10_resultat_echelle', 'Redimensionnement', 'Cadre 220 × 220 avec conservation des proportions', samples[0])
            operations = []
            for action in ('Rotation 90°', 'Miroir H', 'Miroir V'):
                with wait_api(f"images/{single['id']}/transform") as transformed:
                    page.get_by_role('button', name=action, exact=True).click()
                assert transformed.value.status == 201
                operations.append(transformed.value.json()['id'])

            goto(f"/features/{single['id']}", 'Descripteurs visuels')
            for index, tab in enumerate(('Histogramme HSV', 'Moments couleur', 'Couleurs dominantes', 'GLCM', 'LBP'), 11):
                page.get_by_role('button', name=tab, exact=True).click()
                page.get_by_role('button', name=tab, exact=True).scroll_into_view_if_needed()
                capture(f'application/{index:02d}_{tab.lower().replace(" ", "_")}', tab,
                        'Calcul de l’image chargée puis sélection de l’onglet', samples[0])
            goto('/search', 'Recherche CBIR')
            page.get_by_role('button', name='Choisir une image').click()
            picker = page.get_by_placeholder('Rechercher une image...')
            picker.fill('0_1.jpg')
            expect(page.get_by_role('button', name='0_1.jpg', exact=True)).to_be_visible()
            page.get_by_role('button', name='0_1.jpg', exact=True).click()
            page.locator('select').select_option('10')
            capture('cbir/16_requete', 'Choix de requête', 'Sélection de la photographie GHIM originale dans le sélecteur', samples[0])
            with wait_api('cbir/search') as start_response:
                page.get_by_role('button', name='Lancer la recherche').click()
            initial = start_response.value.json()
            q = initial['query_image']['id']
            assert q not in [r['image_id'] for r in initial['results']]
            assert len(initial['results']) == 10
            assert [r['distance'] for r in initial['results']] == sorted(r['distance'] for r in initial['results'])
            expect(page.locator('[data-result-id]')).to_have_count(10)
            capture('cbir/17_recherche_initiale', 'Recherche initiale', 'Classement de dix images à poids uniformes', samples[0])

            state = initial
            for iteration in (1, 2):
                relevant = [r for r in state['results'] if r['image']['category_id'] == initial['query_image']['category_id']]
                negative = [r for r in state['results'] if r not in relevant]
                assert relevant
                for row in relevant[:2]:
                    card = page.locator(f"[data-result-id='{row['image_id']}']")
                    card.get_by_role('button', name='✓ Pertinent', exact=True).click()
                negative_id = (negative or relevant[2:])[0]['image_id']
                card = page.locator(f"[data-result-id='{negative_id}']")
                card.get_by_role('button', name='✗ Non pertinent', exact=True).click()
                if iteration == 1:
                    page.get_by_role('button', name='✓ Pertinent', exact=True).first.scroll_into_view_if_needed()
                    capture('cbir/18_jugements', 'Jugements de pertinence', 'Labels positifs, négatif et neutres dans le même résultat', samples[0])
                with wait_api('cbir/feedback') as feedback:
                    page.get_by_role('button', name=re.compile('Appliquer Re-weighting')).click()
                assert feedback.value.status == 200, feedback.value.text()
                state = feedback.value.json()
                assert len(state['weights']) == 93 and state['iteration'] == iteration
                expect(page.get_by_role('button', name=re.compile(f'Itération {iteration+1}'))).to_be_visible()
                page.evaluate('scrollTo(0,0)')
                capture(f'cbir/{18+iteration:02d}_iteration_{iteration}', f'Itération {iteration}', 'Reclassement après envoi des jugements', samples[0])
            page.get_by_role('heading', name='Poids par groupe de descripteurs').scroll_into_view_if_needed()
            capture('cbir/21_poids', 'Poids Type-1', 'Moyenne de poids dans les cinq familles après deux retours', samples[0])
            page.get_by_role('heading', name='Historique des itérations').scroll_into_view_if_needed()
            capture('cbir/22_precision_rappel', 'Précision et rappel', 'Courbe et historique des itérations 0 à 2', samples[0])
            goto('/analytics', 'Analytiques CBIR')
            expect(page.get_by_role('heading', name='État de l\'index CBIR')).to_be_visible()
            capture('application/23_analytiques', 'Analytiques', 'Statistiques et sessions réellement enregistrées')
            (evidence / 'browser_sessions.json').write_text(json.dumps(
                {'initial': initial, 'iteration_2': state,
                 'transformations': {'original': single, 'crop': cropped, 'resize': resized}}, ensure_ascii=False, indent=2))

            # Destructive steps target only the temporary records.
            ids = [first['id'], second['id'], cropped['id'], resized['id'], *operations]
            token = page.evaluate("localStorage.getItem('access_token')")
            headers = {'Authorization': 'Bearer ' + token}
            assets = os.environ.get('VV_TRANSFORM_ASSETS')
            if assets:
                folder = Path(assets)
                folder.mkdir(parents=True, exist_ok=True)
                for label, item in [('original', single), ('crop', cropped), ('resize', resized)]:
                    response = page.request.get(BASE+f"/api/v1/images/{item['id']}/download", headers=headers)
                    assert response.ok
                    (folder / f'{label}.jpg').write_bytes(response.body())
            assert page.request.post(BASE+'/api/v1/images/bulk-delete', headers=headers, data={'ids': ids}).json()['deleted'] == len(ids)
            assert page.request.delete(BASE+f"/api/v1/images/{single['id']}", headers=headers).ok
            assert page.request.delete(BASE+f"/api/v1/categories/{parent['id']}", headers=headers).ok
            assert page.request.delete(BASE+f"/api/v1/categories/{child['id']}", headers=headers).ok
            status = page.request.get(BASE+'/api/v1/index/status', headers=headers).json()
            assert status['indexed_count'] == status['total_images'] == 9998
            page.get_by_role('button', name='Se déconnecter').click()
            expect(page).to_have_url(re.compile('/login$'))
            assert page.evaluate("localStorage.getItem('access_token')") is None
            page.goto(BASE+'/gallery')
            expect(page).to_have_url(re.compile('/login$'))
            assert network_errors == [(401, '/api/v1/auth/login')]
            assert not page_errors
            assert all('401' in message for message in console_errors)
        finally:
            (evidence / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            (evidence / 'browser_diagnostics.json').write_text(json.dumps(
                {'page_errors': page_errors, 'console_errors': console_errors, 'http_errors': network_errors}, indent=2))
            if len(manifest) < 23:
                page.screenshot(path=tmp_path / 'last-state.png')
            browser.close()
