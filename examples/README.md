# ProSOFT-logge på dit dashboard

Her er komplette eksempler med begge henteknapper og to tabeller med **dato, klokkeslæt og indhold**. Vælg fil efter den editor, du bruger. Kort-YAML og dashboard-YAML er forskellige formater; den tidligere vejledning gjorde ikke denne forskel tydelig nok.

## Vælg den rigtige fil

| Det vil du gøre | Fil | Første YAML-linje |
| --- | --- | --- |
| Tilføje ét almindeligt kort | [prosoft-logs-card.yaml](prosoft-logs-card.yaml) | `type: vertical-stack` |
| Oprette et helt nyt dashboard | [prosoft-logs-dashboard.yaml](prosoft-logs-dashboard.yaml) | `views:` |
| Tilføje efter et kort i en eksisterende YAML-liste | [prosoft-logs-card-list-item.yaml](prosoft-logs-card-list-item.yaml) | `- type: vertical-stack` |
| Tilføje ét Ultra Card | [prosoft-logs-ultra-card.yaml](prosoft-logs-ultra-card.yaml) | `type: custom:ultra-card` |
| Oprette et nyt dashboard med Ultra Card | [prosoft-logs-ultra-dashboard.yaml](prosoft-logs-ultra-dashboard.yaml) | `views:` |

Åbn filen på GitHub og vælg **Raw**, eller brug GitHubs knap til at kopiere filens indhold. Kopiér hele filen. Tilføj ikke selv `title`, `type`, `cards` eller `views` før filen.

## Før du indsætter

Installér ProSOFT-integration **v0.3.12 eller nyere**, genstart Home Assistant, og hent loggene igen. Eksemplerne bruger disse fire id'er fra en installation med enheden i Værksted:

```text
button.vaerksted_aqua_danmark_prosoft_10_hent_parameterlog
button.vaerksted_aqua_danmark_prosoft_10_hent_haendelseslog
sensor.vaerksted_aqua_danmark_prosoft_10_parameterlog
sensor.vaerksted_aqua_danmark_prosoft_10_haendelseslog
```

Kontrollér dem under **Udviklerværktøjer → Tilstande**. Erstat alle forekomster i den valgte fil, hvis dine id'er er anderledes. Sensorernes id'er står flere steder. Et forkert id bliver ikke rettet ved at ændre visningsnavnet.

## Ét kort i et eksisterende dashboard

1. Åbn den fane, kortet skal ligge på, og vælg **Redigér dashboard**.
2. Vælg **Tilføj kort → Manuelt** (i et dashboard med sektioner: tilføj kortet i den ønskede sektion).
3. Erstat hele indholdet i **kortets** kodeeditor med `prosoft-logs-card.yaml` eller `prosoft-logs-ultra-card.yaml`.
4. Gem kortet. Det indeholder selv knapperne og begge loglister.

Denne editor modtager ét objekt med `type:` øverst. Indsæt ikke koden efter et andet korts `type:` i samme editor. Skal det være endnu et kort, brug **Tilføj kort** igen.

## Et helt nyt dashboard

1. Opret et nyt, tomt dashboard til loggene og åbn det.
2. Åbn dashboardets **rå konfigurationseditor** fra redigeringsmenuen.
3. Erstat indholdet med hele `prosoft-logs-dashboard.yaml` eller `prosoft-logs-ultra-dashboard.yaml`.
4. Gem. Filen indeholder allerede `views:`, én fane og det samlede kort.

Brug kun denne erstatning på et nyt/tomt dashboard. På et eksisterende dashboard vil den erstatte de andre faner.

## Efter et eksisterende kort i rå dashboard-YAML

Brug `prosoft-logs-card-list-item.yaml`. Indsæt hele filens listeelement under den relevante `cards:`-liste. Indryk alle linjer lige meget, så første `- type:` flugter med de andre kort. Eksempel på placeringen:

```yaml
views:
  - title: Mit dashboard
    type: masonry
    cards:
      - type: markdown
        content: Mit eksisterende kort
      # Indsæt hele listeelementet her, med seks mellemrum foran første bindestreg.
```

I et dashboard med sektioner hører kortet til i den ønskede sektions `cards:`-liste under `sections:`. Indsæt det ikke i `views:`-listen; den indeholder faner, ikke kort.

## Ultra Card

Ultra-eksemplerne bruger Ultra Cards `native_card`-moduler: ét Entities-kort og to Markdown-kort i samme Ultra Card. Du kan efterfølgende tilpasse layoutet i Ultra Cards visuelle editor. Ingen PRO-moduler bruges.

Ultra Card skal være installeret via HACS, og frontendressourcen skal være indlæst i browseren. Hele Ultra YAML-filen er **en kortkonfiguration**, ikke et enkelt moduls `card_config` og ikke en preset-import. Brug den i kortets kodeeditor som beskrevet ovenfor.

Formatet er kontrolleret mod [Ultra Card 3.14.2-kildekoden](https://github.com/WJDDesigns/Ultra-Card/tree/3cc821b23b01942f6453740f56e815b12bc62fef), herunder `layout.rows`, kolonner og `native_card`-moduler. Vi har ikke verificeret eksemplet i en kørende Ultra Card-frontend eller i ældre versioner.

## Fejl og hvad de betyder

| Fejl | Hvad der skal undersøges |
| --- | --- |
| `At path: views — Expected an array ... undefined` | Editorens format kræver et helt dashboard. Brug dashboardfilen med `views:`. |
| `end of the stream or a document separator is expected` | Kontrollér om et listeelement og et kortobjekt er blandet på samme niveau, eller om to konfigurationer er sat direkte efter hinanden. Brug én komplet fil til den valgte editor. |
| `Custom element doesn't exist: ultra-card` | Ultra Card-ressourcen er ikke indlæst. Kontrollér installation og dashboardressourcer; genindlæs browseren efter installation. |
| Entitet findes ikke | Kontrollér de fire id'er. |
| Henteknap vises, men ingen poster | Kontrollér integrationens version og sensorens `entries`, `status` og `error`. Hent loggen igen efter genstart. |
| Kun “Konfigurationsfejl” | Det er ikke nok til at fastslå årsagen. Gem YAML'en og tag et billede af editoren og fejlen; en gyldig YAML-fil alene beviser ikke, at frontendvisningen virker. |

## Hvad der er kontrolleret

Filerne bliver kontrolleret for YAML-struktur og ens indhold på tværs af kort- og dashboardeksempler. Markdown-skabelonerne er renderet med testdata for fyldt, tom, utilgængelig, hentende og fejlet sensor. Det er **ikke** en fuld test i din Home Assistant eller Ultra Card-browser.

Loggene hentes ved knaptryk. De gemmes i hukommelsen og skal hentes igen efter genstart. Poster sorteres efter anlæggets registrerede dato og tid; fabriksdatoer og dubletter bevares. Afslutning ved inaktivitet vises som ikke bekræftet fuldstændig.
