// https://developers.google.com/chart/interactive/docs/gallery/geochart#Regions
MEDLEY.maps = (function () {
    'use strict';

    google.load("visualization", "1", {packages:["geochart"]});

    const subContinentMap = [
        ['015', 'Northern Africa', 'DZ, EG, EH, LY, MA, SD, TN'],
        ['011', 'Western Africa', 'BF, BJ, CI, CV, GH, GM, GN, GW, LR, ML, MR, NE, NG, SH, SL, SN, TG'],
        ['017', 'Middle Africa', 'AO, CD, ZR, CF, CG, CM, GA, GQ, ST, TD'],
        ['014', 'Eastern Africa', 'BI, DJ, ER, ET, KE, KM, MG, MU, MW, MZ, RE, RW, SC, SO, TZ, UG, YT, ZM, ZW'],
        ['018', 'Southern Africa', 'BW, LS, NA, SZ, ZA'],
        ['154', 'Northern Europe', 'GG, JE, AX, DK, EE, FI, FO, GB, IE, IM, IS, LT, LV, NO, SE, SJ'],
        ['155', 'Western Europe', 'AT, BE, CH, DE, DD, FR, FX, LI, LU, MC, NL'],
        ['151', 'Eastern Europe', 'BG, BY, CZ, HU, MD, PL, RO, RU, SU, SK, UA'],
        ['039', 'Southern Europe', 'AD, AL, BA, ES, GI, GR, HR, IT, ME, MK, MT, CS, RS, PT, SI, SM, VA, YU'],
        ['021', 'Northern America', 'BM, CA, GL, PM, US'],
        ['029', 'Caribbean', 'AG, AI, AN, AW, BB, BL, BS, CU, DM, DO, GD, GP, HT, JM, KN, KY, LC, MF, MQ, MS, PR, TC, TT, VC, VG, VI'],
        ['013', 'Central America', 'BZ, CR, GT, HN, MX, NI, PA, SV'],
        ['005', 'South America', 'AR, BO, BR, CL, CO, EC, FK, GF, GY, PE, PY, SR, UY, VE'],
        ['143', 'Central Asia', 'TM, TJ, KG, KZ, UZ'],
        ['030', 'Eastern Asia', 'CN, HK, JP, KP, KR, MN, MO, TW'],
        ['034', 'Southern Asia', 'AF, BD, BT, IN, IR, LK, MV, NP, PK'],
        ['035', 'South-Eastern Asia', 'BN, ID, KH, LA, MM, BU, MY, PH, SG, TH, TL, TP, VN'],
        ['145', 'Western Asia', 'AE, AM, AZ, BH, CY, GE, IL, IQ, JO, KW, LB, OM, PS, QA, SA, NT, SY, TR, YE, YD'],
        ['053', 'Australia and New Zealand', 'AU, NF, NZ'],
        ['054', 'Melanesia', 'FJ, NC, PG, SB, VU'],
        ['057', 'Micronesia', 'FM, GU, KI, MH, MP, NR, PW'],
        ['061', 'Polynesia', 'AS, CK, NU, PF, PN, TK, TO, TV, WF, WS']
    ];

    function getSubcontinentCode (countryCode) {
        const twoLetterCountryCode = countryCode.substr(0, 2);
        const match = subContinentMap.filter((subcontinent) => {
            return (subcontinent[2].indexOf(twoLetterCountryCode) > -1);
        });

        if (match) {
            return match[0][0];
        }

        return null;
    }

    function createDataTable(latitude, longitude) {
        if (latitude && longitude) {
            return google.visualization.arrayToDataTable([
                ['Latitude', 'Longitude', 'ColorIndex', 'Size'],
                [latitude, longitude, 0, 1]
            ]);
        }

        return google.visualization.arrayToDataTable([
            ['Location', 'ColorIndex', 'Size'],
            [location, 0, 1]
        ]);
    }

    return {
        draw: function () {
            const nodes = Array.from(document.getElementsByClassName('map'));

            nodes.forEach((node) => {
                const latitude = parseFloat(node.dataset.latitude, 10);
                const longitude = parseFloat(node.dataset.longitude, 10);
                const region = node.dataset.region;
                const location = node.dataset.location;
                const dataTable = createDataTable(latitude, longitude);

                const options = {
                    colorAxis: {
                        colors: ['#336699']
                    },
                    displayMode: 'regions',
                    legend: 'none',
                    enableRegionInteractivity: false,
                    region: getSubcontinentCode(region),
                    tooltip: {
                        trigger: 'none'
                    }
                };


                if (latitude && longitude) {
                    options.displayMode = 'markers';
                }

                if (region.substr(0, 2) === 'US') {
                    options.resolution = 'provinces';
                    options.region = region;
                }

                const map = new google.visualization.GeoChart(node);
                map.draw(dataTable, options);
            });
        }
    }
})();

google.setOnLoadCallback(MEDLEY.maps.draw);
