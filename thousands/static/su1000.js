var INITIAL_COORDINATES = [ 54.6829976, 59.2835566 ]
var MSG_SERVER_ERROR = "Невозможно выполнить операцию: ошибка сервера"

function apiCall(uri, callback) {
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open('GET', uri, true);
    xmlhttp.onreadystatechange = function() {
        if ( xmlhttp.readyState == 4 ) {
            if ( xmlhttp.status == 200 ) {
                callback(JSON.parse(xmlhttp.responseText));
            }
        }
    }
    xmlhttp.send(null);

}

function createMap(container, center, zoom) {
    var topo = new L.TileLayer('http://maps.marshruty.ru/ml.ashx?al=1&i=1&x={x}&y={y}&z={z}', {
        maxZoom: 15,
        minZoom: 8,
        attribution: "Генштабовские топокарты используют сервис <a href=\"http://www.marshruty.ru/Maps/Maps.aspx\">карты Маршруты.Ру</a>"
    }); 
    var osm = new L.TileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        minZoom: 8,
        attribution: "&copy; Участники <a href=\"http://www.openstreetmap.org/copyright\">OpenStreetMaps</a>"
    });
    var gs = new L.Google('SATELLITE', {
        maxZoom: 20,
        minZoom: 8
    });

    var map = L.map(container, { center: center, zoom: zoom, layers: osm  });
    var baseMaps = {
        "OpenStreetMaps": osm,
        "Топокарты": topo,
        "Google Sattelite": gs
    };
    L.control.layers(baseMaps).addTo(map);

    return map;
}

function pointPopupCode(feature) {
    name_alt = feature.properties.name_alt == "" ? "" : "<br/>(" + feature.properties.name_alt + ")";
    name = "<a href=\"/summit/" + feature.id + "\">" + feature.properties.name + "</a>";
    return name + name_alt +
        "<br/>Высота: " + feature.properties.height + 
        "<br/>Хребет:" + feature.properties.ridge;
}

function placePoints(data) {
    L.geoJson(data, {
        pointToLayer: function (feature, latlng) {
            var icon = L.MakiMarkers.icon({icon: "marker", color: "#" + feature.properties.color, size: "s"});
            return L.marker(latlng, {icon: icon}).bindPopup(pointPopupCode(feature));
        }
    }).addTo(map);
}

function fillSummitsTable(data) {
    var tb = document.getElementById("summitsTable").getElementsByTagName("tbody")[0];
    tb.innerHTML = '';
    data.features.forEach(function(f) {
        var tr = document.createElement("tr");
        var name_alt = f.properties.name_alt == "" ? "" : " (" + f.properties.name_alt + ")";
        tr.innerHTML = "<td>" + f.properties.number + "</td>" +
            "<td class=\"text-left\"><a href=\"/summit/" + f.id + "\">" + f.properties.name + name_alt + "</a></td>" +
            "<td>" + f.properties.height + "</td>" +
            "<td>" + f.properties.ridge + "</td>" 
        tb.appendChild(tr);
    });
}

function createMainMap() {
    map = createMap('map', INITIAL_COORDINATES, 8);
    var hash = new L.Hash(map);
    apiCall('/api/summits', placePoints);
}


function reorderSummitsTable() {
    if ( window.location.hash == '#orderByHeight' ) {
        apiCall('/api/summits?orderByHeight', fillSummitsTable);
        $('#orderSummitsByRidge').parent('li').removeClass('active');
        $('#orderSummitsByHeight').parent('li').addClass('active');
    } else {
        apiCall('/api/summits', fillSummitsTable);
        $('#orderSummitsByRidge').parent('li').addClass('active');
        $('#orderSummitsByHeight').parent('li').removeClass('active');
    }     
}

function setupCoordinatesPickMap() {
    map = createMap('coordinates-pick-map', INITIAL_COORDINATES, 8);
    map.scrollWheelZoom.disable();
    document.getElementsByClassName('leaflet-container')[0].style.cursor = 'crosshair';

    coordinates_field = document.getElementById('summit_edit_form').coordinates.value;
    if ( coordinates_field ) {
        lat = parseFloat(coordinates_field.split(' ')[0]);
        lng = parseFloat(coordinates_field.split(' ')[1]);
        marker = L.marker(L.latLng(lat, lng));
        marker.addTo(map);
    }
    map.on('click', getPointCoordinates);
}

function getPointCoordinates(e) {
    document.getElementById('summit_edit_form').coordinates.value = e.latlng.lat + ' ' + e.latlng.lng;
    if (marker != null) {
        map.removeLayer(marker);
    }
    marker = L.marker(e.latlng);
    marker.addTo(map);
}
