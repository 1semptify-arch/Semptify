from app.main import app
print('App initialized successfully')
print('Routers registered:')
for route in app.routes:
    print(f'  {route.path} - {route.methods}')