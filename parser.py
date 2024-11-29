from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib.request
import sys
import rfeed
from ics import Calendar, Event, Organizer
import pytz

timezone = pytz.timezone('Europe/Paris')

image_url = 'https://extranet-clubalpin.com/app/out/'

def isValInLst(val, lst):
    return [index for index, content in enumerate(lst) if val in content]

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    sortie_liste = soup.find('div', {'id': 'sortie_liste'})
    sortie_array = sortie_liste.findAll('div', {'class': 'sortie'})
    print(sortie_array)

    results = []
    for sortie in sortie_array:
        print('========')
        intitule_tag = sortie.find('div', {'class': 'intitule'})
        # strip title from link
        title = intitule_tag.find('a').text.strip()
        # get data-sortie-id from a tag
        sortie_id = intitule_tag.find('a')['data-sortie-id']

        inscription_url = ''
        inscription_url_tag = sortie.find('a', {'class': 'packClub'})
        if (inscription_url_tag):
            inscription_url = inscription_url_tag['href']

        # get text from intitule_tag after the title div
        date_str = intitule_tag.next_sibling.strip()
        date_start = ""
        date_end = ""
        all_day=False
        # convert date to ical format
        if date_str.startswith('le'): # same day
            # Date format is one of the following:
            # date_str:  le 09/01/2025 de 09:45 à 16:30
            # date_str:  le 09/01/2025
            # make date look like 09/01/2025, 09:45 and 09/01/2025, 16:30
            date_arr = date_str.strip('le ').split(' de ')
            if(len(date_arr) == 1): # No hours provided
                date_start_str = date_arr[0] + ', 00:00'
                date_end_str = date_arr[0] + ', 23:59'
                all_day = True
            else: # Start and end hours provided
                date_start_str = date_arr[0] + ', ' + date_arr[1].split(' à ')[0]
                date_end_str = date_arr[0] + ', ' + date_arr[1].split(' à ')[1]
            date_start = datetime.strptime(date_start_str, "%d/%m/%Y, %H:%M")
            date_end = datetime.strptime(date_end_str, "%d/%m/%Y, %H:%M")
        else: # date range
            date_arr = date_str.split('du ')[1].split(' au ')
            date_time_start_arr = date_arr[0].split("  à ")
            date_start_str = ', '.join(date_time_start_arr).strip()
            date_time_end_arr = date_arr[1].split(" à ")
            date_end_str = ', '.join(date_time_end_arr).strip()
            print(date_time_start_arr)
            print(date_start_str)
            print(date_time_end_arr)
            print(date_end_str)
            # now we get date with the following format
            # date_start_arr = '08/02/2025, 07:00'
            # or date_start_arr = '08/02/2025'
            # parse date into ical format
            if len(date_time_start_arr) == 2: # No hours provided
                date_start = datetime.strptime(date_start_str, "%d/%m/%Y, %H:%M")
            else:
                date_start = datetime.strptime(date_start_str, "%d/%m/%Y")

            if len(date_time_end_arr) == 2:
                date_end = datetime.strptime(date_end_str, "%d/%m/%Y, %H:%M")
            else:
                date_end = datetime.strptime(date_end_str, "%d/%m/%Y")

        activite_image_tag = sortie.find('img', {'class': 'activite'})
        activite_image = image_url + activite_image_tag['src']
        # get parent div
        parent = activite_image_tag.parent
        activite_nom = parent.text.strip()
        # get lieu
        lieu = sortie.find('div', {'class': 'lieu'}).text.strip()

        # Find div with containing text 'Difficulté'
        # Difficulté can either be:
        # - Tout niveaux
        # - or two images corresponding to:
        #   - Niveau physique
        #   - Niveau technique

        difficulte_tag = sortie.find('div', text='Difficulté')
        difficulte = ""
        niveau_technique=""
        niveau_physique=""
        niveau_technique_img=""
        niveau_physique_img=""
        # get img tag with title "Niveau physique"
        niveau_physique_tag = difficulte_tag.find_next_sibling('img', {'title': 'Niveau physique'})
        if niveau_physique_tag:
            niveau_technique_tag = difficulte_tag.find_next_sibling('img', {'title': 'Niveau technique'})
            niveau_technique_img = image_url + niveau_technique_tag['src']
            niveau_physique_img = image_url + niveau_physique_tag['src']
            print("Niveau physique: ", niveau_physique_img)
            print("Niveau technique: ", niveau_technique_img)

            NIVEAU_PHYSIQUE_MAP = {
                '42': '4',
                '38': '3',
                '34': '2',
                '30': '1',
                '26': '1',
            }
            NIVEAU_TECHNIQUE_MAP = {
                '34': '4',
                '30': '3',
                '26': '2',
                '22': '1',
                '18': '1'
            }

            # url is image.php?type=physique&amp;id=30
            # get id from url
            niveau_physique_id = niveau_physique_img.split('id=')[1]
            niveau_physique = NIVEAU_PHYSIQUE_MAP.get(niveau_physique_id, "Inconnu: " + niveau_physique_img)
            niveau_technique_id = niveau_technique_tag['src'].split('id=')[1]
            niveau_technique = NIVEAU_TECHNIQUE_MAP.get(niveau_technique_id, "Inconnu: " + niveau_technique_img)
        else:
            difficulte = difficulte_tag.next_sibling.strip()
            niveau_technique = difficulte
            niveau_physique = difficulte

        denivele_tag = sortie.find_next('div', {'class': 'denivele'})
        denivele = ""
        if denivele_tag:
            denivele = denivele_tag.text.strip()
            # ensure there is at most a single space
            denivele = ' '.join(denivele.split())
            print(denivele)

        text = [x.strip() for x in sortie.text.split('\n')]
        # find 'Responsable :' and next element in list
        responsable = text[text.index('Responsable :')+1]

        places = ""
        # Places can be:
        # - Capacite illimitée
        # - 9/12 inscriptions confirmées

        if isValInLst('Capacite illimitée', text):
            places = 'Capacite illimitée'
        elif isValInLst('inscriptions confirmées', text):
            id = isValInLst('inscriptions confirmées', text)[0]
            places = text[id]
            if not places.endswith('inscriptions confirmées'):
                places = places.replace('inscriptions confirmées', 'inscriptions confirmées, ')
            if not places.endswith('Capacite illimitée'):
                places = places.replace('Capacité illimitée', 'Capacité illimitée, ')

        STATUS = ["AU PLANNING", "VALIDEE", "ANNULEE"]
        # find if status is in text list
        status = [x for x in STATUS if x in text]
        if status:
            status = status[0]
        else:
            status = 'INCONNU'


        dict = {
            'title': title,
            'sortie_id': sortie_id,
            'inscription_url': inscription_url,
            'activite_image': activite_image,
            'activite': activite_nom,
            'lieu': lieu,
            'date_str': date_str,
            'date_start': date_start,
            'date_end': date_end,
            'all_day': all_day,
            'difficulte': difficulte,
            'niveau_technique': str(niveau_technique),
            'niveau_technique_img': niveau_technique_img,
            'niveau_physique': str(niveau_physique),
            'niveau_physique_img': niveau_physique_img,
            'denivele': denivele,
            'places': places,
            'responsable': responsable,
            'status': status
        }
        results.append(dict)

    return results

def printSorties(results):
    for r in results:
        print('title: ', r['title'])
        print('sortie_id: ', r['sortie_id'])
        print('inscription_url: ', r['inscription_url'])
        print('activite_image: ', r['activite_image'])
        print('activite: ', r['activite'])
        print('lieu: ', r['lieu'])
        print('date_str: ', r['date_str'])
        print('date start: ', r['date_start'])
        print('date end: ', r['date_end'])
        print('difficulte: ', r['difficulte'])
        print('niveau_technique: ', r['niveau_technique'])
        print('niveau_physique: ', r['niveau_physique'])
        if(r['niveau_technique_img']):
            print('niveau_technique_img: ', r['niveau_technique_img'])
        print('niveau_physique: ', r['niveau_physique'])
        if(r['niveau_physique_img']):
            print('niveau_physique_img: ', r['niveau_physique_img'])
        print('denivele: ', r['denivele'])
        print('places: ', r['places'])
        print('responsable: ', r['responsable'])
        print('status: ', r['status'])

def genICAL(results):
    ics = Calendar()
    ics.creator = "CAF Montpellier - https://arntanguy.github.io/caf_montpellier"

    for r in results:
        event = Event()
        event.name = "[" + r['activite'] + "] " + r['title']
        event.begin = r['date_start']
        event.end = r['date_end']
        if r['all_day']:
            event.make_all_day()
        event.uid = r['sortie_id'] + "@arntanguy.github.io/caf_montpellier/agenda_caf.ical"
        event.location = r['lieu']
        event.description = "Sortie: " + r['title'] + "\nLieu: " + r['lieu'] + "\nDate: " + r['date_str'] + "\nNiveau technique: " + r['niveau_technique'] + "\nNiveau physique: " + r['niveau_physique'] + "\nDenivele: " + r['denivele'] + "\nPlaces: " + r['places'] + "\nResponsable: " + r['responsable'] + "\nStatus: " + r['status']
        if r['inscription_url']:
            event.description += "\nInscriptions: " + r['inscription_url']
            event.url = r['inscription_url']

        status = ""
        if r['status'] == 'AU PLANNING':
            status = "TENTATIVE"
        elif r['status'] == 'VALIDEE':
            status = "CONFIRMED"
        elif r['status'] == 'CANCELLED':
            status = "CANCELLED"
        event.status = status

        organizer = Organizer(email="", common_name="CAF Montpellier")
        event.organizer = organizer

        event.last_modified = datetime.now(timezone)
        ics.events.add(event)

    return ics

def genRSS(results):
    items = []
    for r in results:
        item = rfeed.Item(
            title = "[" + r['activite'] + "] " + r['title'],
            link = r['inscription_url'],
            description = """
                <ul>
                    <li><b>Sortie:</b> {title}</li>
                    <li><b>Lieu:</b> {lieu}</li>
                    <li><b>Niveau technique:</b> {niveau_technique}<br /><img src="{niveau_technique_img}" alt="Niveau {niveau_technique}"/></li>
                    <li><b>Niveau physique:</b> {niveau_physique}<br /><img src="{niveau_physique_img}" alt="Niveau {niveau_physique}"/></li>
                    <li><b>Dénivele:</b> {denivele}</li>
                    <li><b>Places:</b> {places}</li>
                    <li><b>Responsable:</b> {responsable}</li>
                    <li><b>Status:</b> {status}</li>
                    <li><b>Activité:</b> {activite}</li>
                    <li><b>Inscriptions:</b> <a href="{link}">{link}</a></li>
                </ul>""".format(
                title = r['title'],
                lieu = r['lieu'],
                niveau_technique = r['niveau_technique'],
                niveau_technique_img = r['niveau_technique_img'],
                niveau_physique = r['niveau_physique'],
                niveau_physique_img = r['niveau_physique_img'],
                denivele = r['denivele'],
                places = r['places'],
                responsable = r['responsable'],
                status = r['status'],
                activite = r['activite'],
                link = r['inscription_url']),
            author = r['responsable'],
            guid = rfeed.Guid(r['sortie_id']),
            pubDate = r['date_start'])
        items.append(item)
    feed = rfeed.Feed(
        title = "Agenda CAF Montpellier",
        link = "https://extranet-clubalpin.com/app/out/out.php?s=12&c=3400&h=32cdfd3f91",
        description = "Agenda des sorties du Club Alpin Français de Montpellier",
        language = "fr-FR",
        lastBuildDate = datetime.now(timezone),
        items = items)
    return feed


# main function
def main():
    # parse main args: save url
    save_ical_url=""
    if len(sys.argv) > 1:
        save_ical_url = sys.argv[1]
    else:
        save_ical_url = "/tmp/sorties_caf.ical"

    save_rss_url=""
    if len(sys.argv) > 2:
        save_rss_url = sys.argv[2]
    else:
        save_rss_url = "/tmp/sorties_caf.rss"

    agenda_url=""
    if(len(sys.argv) > 3):
        agenda_url = sys.argv[3]
    else:
        agenda_url = 'https://extranet-clubalpin.com/app/out/out.php?s=12&c=3400&h=32cdfd3f91'

    html_content = ""
    if agenda_url:
        response = urllib.request.urlopen(agenda_url)
        html_content = response.read().decode('utf-8')
    else:
        # read from example.html
        html_content = open('example.html', 'r').read()


    results = parse_html(html_content)
    # results = results[0:5]
    print('Number of sorties: ', len(results))
    print(results)
    printSorties(results)
    ical = genICAL(results)
    # write ical to tmp
    with open(save_ical_url, 'w') as f:
        f.writelines(ical.serialize_iter())

    rss = genRSS(results)
    with open(save_rss_url, 'w') as f:
        f.write(rss.rss())


if __name__ == "__main__":
    main()
