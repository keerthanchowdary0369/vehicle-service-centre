import os
import re
from app import app, get_db

def build_static():
    out_dir = "gh-pages-build"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    routes = [
        ('/', 'index.html'),
        ('/customers', 'customers.html'),
        ('/vehicles', 'vehicles.html'),
        ('/bookings', 'bookings.html'),
        ('/job_cards', 'job_cards.html'),
        ('/inventory', 'inventory.html'),
        ('/billing', 'billing.html')
    ]

    with app.test_client() as client:
        with app.app_context():
            # Trigger DB init if needed
            get_db()
            
            for route, filename in routes:
                response = client.get(route)
                html = response.data.decode('utf-8')
                
                # Rewrite links for static hosting
                html = re.sub(r'href="/"', 'href="index.html"', html)
                html = re.sub(r'href="/customers"', 'href="customers.html"', html)
                html = re.sub(r'href="/vehicles"', 'href="vehicles.html"', html)
                html = re.sub(r'href="/bookings"', 'href="bookings.html"', html)
                html = re.sub(r'href="/job_cards"', 'href="job_cards.html"', html)
                html = re.sub(r'href="/inventory"', 'href="inventory.html"', html)
                html = re.sub(r'href="/billing"', 'href="billing.html"', html)
                
                with open(os.path.join(out_dir, filename), 'w', encoding='utf-8') as f:
                    f.write(html)
                    
    print("Static build complete!")

if __name__ == "__main__":
    build_static()
