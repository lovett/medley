// see https://developers.google.com/chart/interactive/docs/gallery/geochart#Regions
'use strict';

google.load("visualization", "1", {packages:["geochart"]});

var subContinentMap = [];
subContinentMap.push(['015', 'Northern Africa', 'DZ, EG, EH, LY, MA, SD, TN']);
subContinentMap.push(['011', 'Western Africa', 'BF, BJ, CI, CV, GH, GM, GN, GW, LR, ML, MR, NE, NG, SH, SL, SN, TG']);
subContinentMap.push(['017', 'Middle Africa', 'AO, CD, ZR, CF, CG, CM, GA, GQ, ST, TD']);
subContinentMap.push(['014', 'Eastern Africa', 'BI, DJ, ER, ET, KE, KM, MG, MU, MW, MZ, RE, RW, SC, SO, TZ, UG, YT, ZM, ZW']);
subContinentMap.push(['018', 'Southern Africa', 'BW, LS, NA, SZ, ZA']);
subContinentMap.push(['154', 'Northern Europe', 'GG, JE, AX, DK, EE, FI, FO, GB, IE, IM, IS, LT, LV, NO, SE, SJ']);
subContinentMap.push(['155', 'Western Europe', 'AT, BE, CH, DE, DD, FR, FX, LI, LU, MC, NL']);
subContinentMap.push(['151', 'Eastern Europe', 'BG, BY, CZ, HU, MD, PL, RO, RU, SU, SK, UA']);
subContinentMap.push(['039', 'Southern Europe', 'AD, AL, BA, ES, GI, GR, HR, IT, ME, MK, MT, CS, RS, PT, SI, SM, VA, YU']);
subContinentMap.push(['021', 'Northern America', 'BM, CA, GL, PM, US']);
subContinentMap.push(['029', 'Caribbean', 'AG, AI, AN, AW, BB, BL, BS, CU, DM, DO, GD, GP, HT, JM, KN, KY, LC, MF, MQ, MS, PR, TC, TT, VC, VG, VI']);
subContinentMap.push(['013', 'Central America', 'BZ, CR, GT, HN, MX, NI, PA, SV']);
subContinentMap.push(['005', 'South America', 'AR, BO, BR, CL, CO, EC, FK, GF, GY, PE, PY, SR, UY, VE']);
subContinentMap.push(['143', 'Central Asia', 'TM, TJ, KG, KZ, UZ']);
subContinentMap.push(['030', 'Eastern Asia', 'CN, HK, JP, KP, KR, MN, MO, TW']);
subContinentMap.push(['034', 'Southern Asia', 'AF, BD, BT, IN, IR, LK, MV, NP, PK']);
subContinentMap.push(['035', 'South-Eastern Asia', 'BN, ID, KH, LA, MM, BU, MY, PH, SG, TH, TL, TP, VN']);
subContinentMap.push(['145', 'Western Asia', 'AE, AM, AZ, BH, CY, GE, IL, IQ, JO, KW, LB, OM, PS, QA, SA, NT, SY, TR, YE, YD']);
subContinentMap.push(['053', 'Australia and New Zealand', 'AU, NF, NZ']);
subContinentMap.push(['054', 'Melanesia', 'FJ, NC, PG, SB, VU']);
subContinentMap.push(['057', 'Micronesia', 'FM, GU, KI, MH, MP, NR, PW']);
subContinentMap.push(['061', 'Polynesia', 'AS, CK, NU, PF, PN, TK, TO, TV, WF, WS']);

var getSubcontinentCode = function (countryCode) {
    var match = subContinentMap.filter(function (subcontinent) {
        if (subcontinent[2].indexOf(countryCode) > -1) {
            return true;
        }
    });

    return match[0][0];
}


var drawMaps = function () {

    var maps = document.getElementsByClassName('map');

    Array.prototype.forEach.call(maps, function (node) {
        var latitude = parseFloat(node.getAttribute('data-latitude'), 10);
        var longitude = parseFloat(node.getAttribute('data-longitude'), 10);
        var region = node.getAttribute('data-region');
        var location = node.getAttribute('data-location');
        var options = {
            colorAxis: {colors: ['#3399cc']},
            datalessRegionColor: '#eef3f6',
            legend: 'none',
            enableRegionInteractivity: false,
            tooltip: {
                trigger: 'none'
            }
        };

        if (latitude && longitude) {
            var dataTable = google.visualization.arrayToDataTable([
                ['Latitude', 'Longitude', 'ColorIndex', 'Size'],
                [latitude, longitude, 0, 1]
            ]);
            options.displayMode = 'markers';
        } else {
            var dataTable = google.visualization.arrayToDataTable([
                ['Location', 'ColorIndex', 'Size'],
                [location, 0, 1]
            ]);
            options.displayMode = 'regions';
        }

        if (region.substr(0, 2) === 'US') {
            options.resolution = 'provinces';
            options.region = region;
        } else {
            options.region = getSubcontinentCode(region);
        }

        var map = new google.visualization.GeoChart(node);
        map.draw(dataTable, options);
    });
};

google.setOnLoadCallback(drawMaps);
