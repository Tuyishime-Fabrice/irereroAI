# Data Sources and Methodology — IrereroAI

IrereroAI combines official Rwandan statistics, geospatial datasets, household surveys, and early childhood development (ECD) standards to support evidence-based planning and monitoring. Where official data was not readily available in a usable format or could not be obtained in time, some information was compiled from publicly available sources or web-extracted and treated as provisional. Policy standards are used as parameters, while simulated caregiver check-ins and learning progress are included solely to demonstrate the platform's functionality, as it has not yet been used by real caregivers.

## Data Storage and Access

For responsible data handling, I stored the project datasets in a **private GitHub repository** rather than publishing them in a public repository. This was a precaution because redistribution permissions were not confirmed for every dataset, and some sources may have access restrictions or data-sharing conditions. Repository access is limited to authorized project collaborators. Private hosting helps prevent unintended public exposure, but it does not replace the need to comply with each dataset's original licence, terms of use, and any applicable data-sharing agreement.

## Data Sources

| Dataset / Source | Institution | Use in IrereroAI |
|---|---|---|
| [Fifth Population and Housing Census (PHC5), 2022](https://www.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/main-indicators-5th-rwanda-population-and-housing-census-phc) | NISR | Population estimates, planning gaps, and household context |
| [WorldPop Rwanda population data, 2020](https://hub.worldpop.org/geodata/summary?id=49708) | University of Southampton / WorldPop | Population distribution and spatial analysis |
| [WorldPop population data, 2015–2030](https://hub.worldpop.org/geodata/summary?id=50514) | University of Southampton / WorldPop | Population distribution and planning estimates |
| [Rwanda Subnational Population Projections, 2023–2032 — Provinces](https://gis.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/rwanda-subnational-population-projections-provinces-2023-2032) and [Districts](https://gis.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/rwanda-subnational-population-projections-districts-2023-2032) | NISR | Population denominators and projection of planning needs |
| [Rwanda Sector Boundaries, 2022](https://services5.arcgis.com/deNm5epdmeZgcm16/ArcGIS/rest/services/Sector_Boundary_2022/FeatureServer/1) | NISR / Rwanda geospatial services | Administrative mapping and geographic data joins |
| [OpenStreetMap Rwanda extract](https://download.geofabrik.de/africa/rwanda.html) | OpenStreetMap contributors / Geofabrik | Mapping nearby facilities and estimating distance to services |
| Rwanda pre-primary school locations and Education Statistical Yearbooks, 2020/21–2024/25 | MINEDUC | School mapping, enrolment trends, and education capacity indicators |
| [Rwanda Demographic and Health Survey (DHS), 2025](https://microdata.worldbank.org/catalog/8555/get-microdata) | NISR, Ministry of Health, and The DHS Program | Child wellbeing and nutrition-related context |
| [Integrated Household Living Conditions Survey (EICV7), 2023/24](https://microdata.statistics.gov.rw/index.php/catalog/119/get_microdata) | NISR | Poverty-related indicators for planning and diagnosis |
| National ECD Standards, 2024 | NCDA | ECD service standards and planning parameters |
| ECD learning and course materials | NCDA, UNICEF, and WHO | Learning content, guidance, and programme parameters |
| NCDA ECD Mapping System extract | NCDA | Potential supply-side information on ECD centres and caregivers; subject to the required data-sharing approval |
| Simulated caregiver check-ins and course progress | IrereroAI synthetic data generator, 2026 | Demonstration of caregiver engagement, learning progress, and platform alerts |

**Data limitations and interpretation:** Some datasets are provisional or subject to access and sharing conditions. Household survey indicators should be interpreted in light of their sampling design and geographic coverage. Simulated records are used only for demonstration and should not be interpreted as actual caregiver activity or programme outcomes.
