class Config:
    SECRET_KEY = 'nbadsjb813bnjc'

class DevelopmentConfig():
    DEBUG=True
    
config = {
    'development': DevelopmentConfig
}