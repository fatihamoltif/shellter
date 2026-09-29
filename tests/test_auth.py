def test_register_valid_user(client, app):
    # Teste le cas valide
    response = client.post('/auth/register', data={
        'username': 'youssef',
        'email': 'youssef@shellter.local',
        'password': 'password_robuste_123'
    })
    assert response.status_code == 302 # Redirection vers login après succès
    
    with app.app_context():
        from app.models import User
        user = User.query.filter_by(username='youssef').first()
        assert user is not None
        # Preuve qu'aucun mot de passe n'est en clair
        assert user.password_hash != 'password_robuste_123'

def test_register_duplicate_user(client):
    # Inscrit un premier utilisateur
    client.post('/auth/register', data={'username': 'test1', 'email': 'test1@test.com', 'password': 'password123'})
    
    # Teste le doublon
    response = client.post('/auth/register', data={'username': 'test1', 'email': 'test1@test.com', 'password': 'password123'})
    assert b"d\xc3\xa9j\xc3\xa0 pris" in response.data # Vérifie que l'erreur s'affiche