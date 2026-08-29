# Pub map — where we've played

Standalone page, deliberately **not** linked to individual games (see project
notes — we only kept game sequence, not dates, so there's no reliable
game-to-venue join).

DAC doesn't have a native map widget, so this is a plain static page: export
`mart_pub_locations` to JSON/CSV and render it with Leaflet (free, no key)
or MapLibre. Sketch:

```html
<!-- pub_map.html -->
<div id="map" style="height: 600px;"></div>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
  fetch('mart_pub_locations.json')
    .then(r => r.json())
    .then(pubs => {
      const map = L.map('map').setView([51.5074, -0.1278], 11); // London default
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
      pubs.filter(p => p.is_confirmed_pub).forEach(p => {
        L.marker([p.lat, p.lng]).addTo(map).bindPopup(p.pub_name);
      });
    });
</script>
```

Export step (run after `mart_pub_locations` is built):

```sql
-- assets/marts/export_pub_locations_json.sql, or just:
copy (select * from mart_pub_locations) to 'dashboard/mart_pub_locations.json';
```

Serve this page alongside the DAC site (same static host, or just open the
HTML file locally).
