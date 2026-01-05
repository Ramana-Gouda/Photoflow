README: Foto-workflow Automatisering (HDR-productie & Pano-voorbereiding) -v47.1
Dit programma automatiseert het organiseren en batch-verwerken van grote hoeveelheden RAW-opnames. Het is specifiek ontworpen om de tijdrovende stappen vóór het stitchen van een panorama uit handen te nemen: het sorteren van reeksen, het produceren van HDR-tussenbestanden en het veiligstellen van een fallback-set (reservefoto's).

Wat doet dit programma?
Sorteert & Schoont op (met Fallback): Groepeert RAW-bestanden automatisch in reeksen (stacks) op basis van tijdstip en belichtingsverschillen. In de hoofdmap blijft alleen de eerste foto van elke reeks (plus alle losse foto's) staan.

Het voordeel: Je houdt een schoon visueel overzicht van je shoot, én je hebt direct een volledige set foto's klaarstaan om een standaard (niet-HDR) panorama te stitchen mocht de HDR-opname onverhoopt onbruikbaar zijn (bijvoorbeeld door 'ghosting' van bewegende takken).

Batch HDR-productie: Voegt volledige mappen met reeksen achter elkaar samen tot hoogwaardige beelden. Keuze uit:
Enfuse (TIFF): Direct ontwikkelde beelden via Darktable.

HDRmerge (DNG): Ruwe 32-bit HDR-bestanden voor maximale nabewerking.

Veilig Verzamelen & Opschonen: Verplaatst alle HDR-resultaten naar de map Verzamelde_HDR_bestanden. Deze map wordt één niveau hoger geplaatst dan de werkmap. Na afloop kan de tijdelijke werkmap veilig worden verwijderd om schijfruimte te besparen.


Belangrijke Instellingen
1. De "Oppepper" (oppepper.xmp)
Voor een correcte kleurweergave zonder oranje of groene zweem bij verschillende cameramerken (Sony, Canon, Panasonic), moet je het bestand oppepper.xmp in de Darktable GUI als volgt voorbereiden:

1  Open een RAW-foto en klik in het paneel Geschiedenis op "alles verwijderen".
2  Zet Witbalans op "Camera".
3  Zet de module Kleurkalibratie (Color Calibration) volledig UIT.
4  Zet gewenste modules zoals Lenscorrectie, Sigmoid en Lokaal contrast aan.
5  Exporteer dit als oppepper.xmp en plaats dit in dezelfde map als het script.

2. Stack-grootte (Tab 1)
Auto: Het script bepaalt zelf de reeks op basis van tijd en belichting.

Vast op 3, 5 of 7: Gebruik dit als je veel reeksen zeer kort achter elkaar hebt geschoten. Het dwingt het script om strikt na elke X foto's een nieuwe reeks te beginnen.


3. Veiligheid (Tab 3)
Het script gebruikt een verborgen marker-bestand (.safe_to_delete). Een map wordt door het programma alleen verwijderd als deze marker aanwezig is en de mapnaam exact overeenkomt. Dit voorkomt dat per ongeluk belangrijke systeemmappen of originele fotomappen worden gewist.


Installatie op Linux Desktop (Arch Linux)
Open de terminal en voer het volgende commando uit om alle benodigdheden te installeren:

 sudo pacman -S pyside6 perl-image-exiftool darktable hugin enblend-enfuse hdrmerge xdg-desktop-portal-kde

(Gebruik xdg-desktop-portal-gnome als je de GNOME-omgeving gebruikt in plaats van KDE).

Uitvoeren
Sla het script op als workflow_hdr.py.
Zorg dat oppepper.xmp in dezelfde map staat.
Maak het script uitvoerbaar en start het:

chmod +x workflow_hdr.py
./workflow_hdr.py


Systeemeisen & Techniek

Processor: Optimaal gebruik van multicore-processors (zoals de Ryzen 3600). Het script benut alle 12 threads voor het uitlijnen en samenvoegen.
Bestandssysteem: Geoptimaliseerd voor Btrfs. Maakt gebruik van reflinks om bestanden direct te kopiëren zonder extra schijfruimte in te nemen. Werkt ook op Ext4 via standaard kopieeracties.
Beeldkwaliteit: Gebruikt de -C (auto-crop) vlag tijdens het uitlijnen om foutieve randen en sensor-artefacten aan de zijden van de foto te voorkomen.
Geheugen: Verwerkt RAW-bestanden serieel per map om te voorkomen dat het systeemgeheugen (16GB) volloopt tijdens de TIFF-conversie.
