var INITIAL_COORDINATES = [ 54.480, 59.041 ]
var MSG_SERVER_ERROR = "Невозможно выполнить операцию: ошибка сервера"


window.addEventListener("load", addDeleteConfirmation);

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
    var osm = new L.TileLayer('https://{s}.tile.thunderforest.com/landscape/{z}/{x}/{y}.png', {
            maxZoom: 20,
            minZoom: 8,
            attribution: "Карты &copy; <a href=\"http://www.thunderforest.com\">Thunderforest</a>, Данные &copy; <a href=\"http://www.openstreetmap.org/copyright\">участники OpenStreetMap</a>"
            });
    var gs = new L.Google('SATELLITE', {
            maxZoom: 20,
            minZoom: 8
            });

    var map = L.map(container, { center: center, zoom: zoom, layers: osm  });
    var baseMaps = {
        "OpenStreetMaps Topo": osm,
        "Генштабовские Топокарты": topo,
        "Спутниковые снимки": gs
    };
    L.control.layers(baseMaps).addTo(map);

    return map;
}

function pointPopupCode(feature) {
    name = "<a href=\"/summit/" + feature.id + "\">" + feature.properties.name + "</a>";
    return name +
        "<br>Высота: " + feature.properties.height + 
        "<br>Хребет: " + feature.properties.ridge;
}

function placePoints(data) {
    L.geoJson(data, {
        pointToLayer: function (feature, latlng) {
            icon_type = feature.properties.climbed ? "embassy" : "marker";
            marker_size = feature.properties.main ? "m" : "s";
            var icon = L.MakiMarkers.icon({icon: icon_type, color: "#" + feature.properties.color, size: marker_size});
            if ( typeof(hl_summit) !== 'undefined' && hl_summit === feature.id ) {
                // ugly workaround due to https://github.com/Leaflet/Leaflet/issues/2488
                popup_toopen = L.marker(latlng, {icon: icon}).bindPopup(pointPopupCode(feature));
                return popup_toopen;
            } else {
                return L.marker(latlng, {icon: icon}).bindPopup(pointPopupCode(feature));
            }
        }
    }).addTo(map);
    if ( typeof popup_toopen !== 'undefined' ) {
        popup_toopen.openPopup();
    }
}

function createMainMap() {
    map = createMap('map', INITIAL_COORDINATES, 8);
    var hash = new L.Hash(map);
    apiCall('/api/summits', placePoints);
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

function deleteEntry() {
    answer = confirm("Вы уверены?");
    if (answer) {
        form = document.getElementById('climb-delete-form');
        form.action = this.href;
        form.submit()
    }
    return false;
}

function addDeleteConfirmation() {
    var confirmed_links = document.getElementsByClassName('simple-delete-confirm');
    for (i = 0; i < confirmed_links.length; i++ ) { 
        //confirmed_links[i].onclick = function() { return confirm("Are you sure?"); 
        confirmed_links[i].onclick = deleteEntry; 
    }
}
