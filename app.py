#Importación de librerías y módulos
from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from config import config
from datetime import datetime
import base64

#Instanciación de objetos para la aplicación
app = Flask(__name__)
app.secret_key = 'smcnkaej42qownafa0ckco2q'
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root@localhost/sigesol10"
db = SQLAlchemy()
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
db.init_app(app)

#Modelos
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombreUsuario = db.Column(db.String(20), unique=True, nullable=False)
    contrasena = db.Column(db.String(102), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    nombreCompleto = db.Column(db.String(50), nullable=False)
    departamento = db.Column(db.String(60), nullable=False)
    unidad = db.Column(db.String(60), nullable=False)
    solicitudes = db.relationship('Solicitud', backref='usuario', lazy=True)
    estados = db.relationship('Estado', backref='usuario', lazy=True)
    
    def __init__(self, id, nombreUsuario, contrasena, rol, nombreCompleto, departamento, unidad):
        self.id = id
        self.nombreUsuario = nombreUsuario
        self.contrasena = contrasena
        self.rol = rol
        self.nombreCompleto = nombreCompleto
        self.departamento = departamento
        self.unidad = unidad

    def get_id(self):
        return (self.id)

    def __repr__(self):
        return f"Usuario('{self.nombreUsuario}')"

class Solicitud(db.Model):
    __tablename__ = 'solicitudes'
    idSolicitud = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False)
    fechaDeIngreso = db.Column(db.Date, default=datetime.now().strftime('%d-%m-%Y'), nullable=False)
    horaDeIngreso = db.Column(db.Time, nullable=False)
    fechaDeVencimiento = db.Column(db.Date, default=datetime.now().strftime('%d-%m-%Y'), nullable=False)
    nombreSolicitante = db.Column(db.String(30), nullable=False)
    materia = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    departamento = db.Column(db.String(60), nullable=False)
    unidad = db.Column(db.String(60))
    usuarioID = db.Column(db.String(30), db.ForeignKey('usuarios.nombreUsuario'), nullable=False)
    estados = db.relationship('Estado', backref='solicitud', lazy=True)

    def __init__(self, idSolicitud, numero, fechaDeIngreso, horaDeIngreso, fechaDeVencimiento, nombreSolicitante, materia, tipo, departamento, unidad, usuarioID):
        self.idSolicitud = idSolicitud
        self.numero = numero
        self.fechaDeIngreso = fechaDeIngreso
        self.horaDeIngreso = horaDeIngreso
        self.fechaDeVencimiento = fechaDeVencimiento
        self.nombreSolicitante = nombreSolicitante
        self.materia = materia
        self.tipo = tipo
        self.departamento = departamento
        self.unidad = unidad
        self.usuarioID = usuarioID

    def __repr__(self):
        return f"Solicitud('{self.idSolicitud}','{self.numero}','{self.fechaDeIngreso}','{self.fechaDeVencimiento}','{self.nombreSolicitante}','{self.materia}','{self.tipo}','{self.departamento}','{self.unidad}','{self.usuarioID}')"

class Estado(db.Model):
    __tablename__ = 'estadoSolicitudes'
    fkIdSolicitud = db.Column(db.Integer, db.ForeignKey('solicitudes.idSolicitud'), primary_key=True, nullable=False)
    idInternoDepto = db.Column(db.Integer, nullable=False, autoincrement=True, unique=True)
    idModificacion = db.Column(db.Integer, primary_key=True)
    nombreUsuario = db.Column(db.String(20), db.ForeignKey('usuarios.nombreUsuario'), nullable=False)
    descripcionProceso = db.Column(db.String(100), nullable=False)
    fechaModificacion = db.Column(db.Date, default=datetime.now().strftime('%d-%m-%Y'), nullable=False)
    designadoA = db.Column(db.String(60), nullable=False)
    estadoActual = db.Column(db.String(20), nullable=False)

    def __init__(self, idInternoDepto, fkIdSolicitud, idModificacion, nombreUsuario, descripcionProceso, fechaModificacion, designadoA, estadoActual):
        self.idInternoDepto = idInternoDepto
        self.fkIdSolicitud = fkIdSolicitud
        self.idModificacion = idModificacion
        self.nombreUsuario = nombreUsuario
        self.descripcionProceso = descripcionProceso
        self.fechaModificacion = fechaModificacion

        self.designadoA = designadoA
        self.estadoActual = estadoActual
    
    def generar_id_interno(self):
        ultima_solicitud = Solicitud.query.filter_by(idInternoDepto=self.idInternoDepto).order_by(Solicitud.idInternoDepto.desc()).first()
        if ultima_solicitud is None:
            return f'{self.departamento.abreviacion}-001'
        else:
            ultimo_id = int(ultima_solicitud.id_interno.split('-')[-1])
            nuevo_id = ultimo_id + 1
            return f'{self.departamento.abreviacion}-{nuevo_id:03d}'

    def __repr__(self):
        return f"Estado de la solicitud('{self.idInternoDepto}','{self.fkIdSolicitud}' modificada N° '{self.idModificacion}' realizada por el usuario '{self.nombreUsuario}' en la fecha '{self.fechaModificacion}','{self.estado}','{self.designadoA}')"

###   Funciones   ###

#Funcion que retorna todos los usuarios registrados en la base de datos
def get_users():
    usuarios = []
    all_usuarios = db.session.execute(db.select(Usuario).order_by(Usuario.id)).scalars()
    for user in all_usuarios:
        usuarios.append({"id":user.id, "nombreUsuario":user.nombreUsuario, "rol":user.rol, "nombreCompleto":user.nombreCompleto, "departamento":user.departamento, "unidad":user.unidad})
    return usuarios

#Funcion que retorna todos las solicitudes registrados en la base de datos
def get_solicitudes():
    solicitudes = []
    #all_solicitudes = Solicitud.query.all()
    all_solicitudes = db.session.execute(db.select(Solicitud).order_by(Solicitud.idSolicitud)).scalars()
    for solicitud in all_solicitudes:
        solicitudes.append({"idSolicitud":solicitud.idSolicitud, "numero":solicitud.numero, "fechaDeIngreso":solicitud.fechaDeIngreso, "horaDeIngreso":solicitud.horaDeIngreso, "fechaDeVencimiento":solicitud.fechaDeVencimiento, "nombreSolicitante":solicitud.nombreSolicitante, "materia":solicitud.materia, "tipo":solicitud.tipo, "departamento":solicitud.departamento, "unidad":solicitud.unidad, "usuarioID":solicitud.usuarioID})
    return solicitudes

#Función que retorna todos los estados de una solicitud
def get_estados():
    estados = []
    #all_solicitudes = Solicitud.query.all()
    all_estados = db.session.execute(db.select(Estado).order_by(Estado.fkIdSolicitud)).scalars()
    for estado in all_estados:
        estados.append({"idInternoDepto":estado.idInternoDepto, "fkIdSolicitud":estado.fkIdSolicitud, "idModificacion":estado.idModificacion, "nombreUsuario":estado.nombreUsuario, "descripcionProceso":estado.descripcionProceso, "fechaModificacion":estado.fechaModificacion, "designadoA":estado.designadoA, "estadoActual":estado.estadoActual})
    return estados

@login_manager.user_loader
def load_user(id):
    usuario = Usuario.query.filter_by(id=id).first()
    return usuario

#####     Rutas     #####
#RUTAS PRINCIPALES Y DE AUTH
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        nombreUsuario = request.form['nombreUsuario']
        contrasena = request.form['contrasena']
        user = Usuario.query.filter_by(nombreUsuario=nombreUsuario).first()
        if user:
            if user.contrasena == contrasena:
                login_user(user)
                if user.rol == 'Administrador':
                    return redirect(url_for('admin'))
                elif user.rol == 'OIRS':
                    return redirect(url_for('oirs'))
                elif user.rol == 'Funcionario':
                    return redirect(url_for('funcionario'))
                elif user.rol == "Secretaria":
                    return redirect(url_for('secretaria'))
                else:
                    flash("Usuario no cuenta con rol, contactar con administrador", 'warning')
                    return redirect(url_for('login'))
            else:
                flash("Contraseña incorrecta", 'danger')
                return redirect(url_for('login'))
        else:
            flash("Nombre de usuario incorrecto", 'danger')
            return redirect(url_for('login'))
    return render_template('views/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

#RUTAS ADMINISTRADOR
@app.route('/admin', methods=['GET','POST'])
@login_required
def admin():
    usuarios = get_users()
    solicitudes = get_solicitudes()
    return render_template('views/admin/admin.html', usuarios=usuarios, solicitudes=solicitudes)

@app.route('/adminCrudUsuarios', methods=['GET','POST'])
@login_required
def adminCrudUsuarios():
    usuarios = get_users()
    if request.method == "POST":
        user = Usuario(
            id = Usuario.id,
            nombreUsuario = request.form['nombreUsuario'],
            contrasena = request.form['contrasena'],
            rol = request.form['rol'],
            nombreCompleto = request.form['nombreCompleto'],
            departamento = request.form['departamento'],
            unidad = request.form['unidad']
        )
        db.session.add(user)
        db.session.commit()
        flash("¡Usuario creado exitosamente!", 'success')
        return redirect(url_for('adminCrudUsuarios'))
    return render_template('views/admin/adminCrudUsuarios.html', usuarios=usuarios)

@app.route('/adminCrudSolicitudes', methods=['GET','POST'])
@login_required
def adminCrudSolicitudes():
    solicitudes = get_solicitudes()
    current_time = datetime.now().time().strftime('%H:%M')
    if request.method == "POST":
        solicitud = Solicitud(
            idSolicitud= request.form['idSolicitud'],
            numero = request.form['numero'],
            fechaDeIngreso = request.form['fechaDeIngreso'],
            horaDeIngreso = request.form['horaDeIngreso'],
            fechaDeVencimiento = request.form['fechaDeVencimiento'],
            nombreSolicitante = request.form['nombreSolicitante'],
            materia = request.form['materia'],
            tipo = request.form['tipo'],
            departamento = request.form['departamento'],
            unidad = request.form['unidad'],
            usuarioID = request.form['funcionario']
        )
        db.session.add(solicitud)
        db.session.commit()
        flash("¡Solicitud creada exitosamente!", 'success')
        return redirect(url_for('adminCrudSolicitudes'))
    return render_template('views/admin/adminCrudSolicitudes.html', solicitudes=solicitudes, current_time=current_time)

#RUTAS OIRS
@app.route('/oirs', methods=['GET','POST'])
@login_required
def oirs():
    solicitudes = get_solicitudes()    
    return render_template('views/oirs/oirs.html', solicitudes=solicitudes)

@app.route('/oirsCrudSolicitudes', methods=['GET','POST'])
@login_required
def oirsCrudSolicitudes():
    solicitudes = get_solicitudes()
    current_time = datetime.now().time().strftime('%H:%M')
    if request.method == "POST":        
        solicitud = Solicitud(
            idSolicitud= request.form['idSolicitud'],
            numero = request.form['numero'],
            fechaDeIngreso = request.form['fechaDeIngreso'],
            horaDeIngreso = request.form['horaDeIngreso'],
            fechaDeVencimiento = request.form['fechaDeVencimiento'],
            nombreSolicitante = request.form['nombreSolicitante'],
            materia = request.form['materia'],
            tipo = request.form['tipo'],
            departamento = request.form['departamento'],
            unidad = request.form['unidad'],
            usuarioID = request.form['funcionario']
        )
        db.session.add(solicitud)
        db.session.commit()
        flash("¡Solicitud creada exitosamente!", 'success')
        return redirect(url_for('oirsCrudSolicitudes'))
    return render_template('views/oirs/oirsCrudSolicitudes.html', solicitudes=solicitudes, current_time=current_time)

#RUTAS SECRETARÍA
@app.route('/secretaria', methods=['GET','POST'])
@login_required
def secretaria():
    return render_template('/views/secretaria/secretaria.html')

@app.route('/secreSolIngresadas', methods=['GET','POST'])
@login_required
def secreSolIngresadas():
    solicitudes = get_solicitudes()
    if request.method == "POST":
        idSolicitud = request.form['idSolicitud']
        return render_template('views/secretaria/asignarUnidad/'.format(idSolicitud))
    return render_template('views/secretaria/secreSolIngresadas.html', solicitudes=solicitudes)

@app.route('/asignarUnidad/<string:nombreUsuario>/<int:idSolicitud>', methods=['GET','POST'])
@login_required
def asignarUnidad(nombreUsuario, idSolicitud):
    if request.method == "POST":
        solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
        unidad = request.form['unidad']
        solicitud.unidad = unidad
        estado = Estado(
            idInternoDepto = request.form['idInternoDepto'],
            fkIdSolicitud = idSolicitud,
            nombreUsuario = nombreUsuario,
            idModificacion = request.form['idModificacion'],
            descripcionProceso = request.form['descripcionProceso'],
            fechaModificacion = request.form['fechaModificacion'],
            designadoA = solicitud.unidad,
            estadoActual = request.form['estadoActual']
        )
        db.session.add(estado)
        db.session.commit()
        return redirect(url_for('secreSolIngresadas'))
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    estado = Estado.query.filter_by(fkIdSolicitud = idSolicitud).first()
    return render_template('views/secretaria/asignarUnidad.html', solicitud=solicitud, estado=estado)
        
@app.route('/<string:departamento>/<string:unidad>', methods=['GET','POST'])
@login_required
def solicitudesunidad(departamento, unidad):
    solicitudes = get_solicitudes()
    return render_template('/views/secretaria/solicitudesUnidad.html', solicitudes=solicitudes, departamento=departamento, unidad=unidad)

@app.route('/estadoSolicitud/<int:idSolicitud>', methods=['GET','POST'])
@login_required
def estadoSolicitud(idSolicitud):    
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    estado = db.session.execute(db.select(Estado).filter_by(fkIdSolicitud=idSolicitud)).scalar_one()
    estados = get_estados()
    return render_template('views/secretaria/estadoSolicitud.html', solicitud=solicitud, estado=estado, estados=estados, idSolicitud=idSolicitud, fkIdSolicitud=idSolicitud)

#RUTAS FUNCIONARIO
@app.route('/funcionario', methods=['GET','POST'])
@login_required
def funcionario():
    return render_template('views/funcionario/funcionario.html')

@app.route('/funSolIngresadas', methods=['GET','POST'])
@login_required
def funSolIngresadas():
    solicitudes = get_solicitudes()
    return render_template('/views/funcionario/funSolIngresadas.html', solicitudes=solicitudes)

@app.route('/funSolPendientes', methods=['GET','POST'])
@login_required
def funSolPendientes():
    solicitudes = get_solicitudes()
    return render_template('/views/funcionario/funSolPendientes.html', solicitudes=solicitudes)

@app.route('/gestionarSolicitud/<int:id>/<int:idSolicitud>/<string:departamento>/<string:unidad>', methods=['GET','POST'])
@login_required
def gestionarSolicitud(id, idSolicitud, departamento, unidad):
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    if request.method == 'POST':
        estado = Estado(
            idInternoDepto = request.form['idInternoDepto'],
            idModificacion = request.form['idModificacion'],
            fkIdSolicitud = request.form['fkIdSolicitud'],
            nombreUsuario = request.form['nombreUsuario'],
            descripcionProceso = request.form['descripcionProceso'],
            fechaModificacion = request.form['fechaModificacion'],
            designadoA = request.form['designadoA'],
            estadoActual = request.form['estadoActual']
        )
        db.session.commit()
        solicitudes = get_solicitudes()
        return render_template('views/funcionario/funSolIngresadas.html',solicitudes=solicitudes)
    estado = db.session.execute(db.select(Estado).filter_by(fkIdSolicitud=idSolicitud)).scalar_one()
    return render_template('views/funcionario/gestionarSolicitud.html', id=id, idSolicitud=idSolicitud, solicitud=solicitud, estado=estado, departamento=departamento, unidad=unidad)


#####     Rutas CRUD     #####

###   UPDATES   ###
#UPDATE USUARIO
@app.route('/editu/<int:id>', methods=['GET','POST'])
@login_required
def edit_usuario(id):
    if request.method == 'POST':
        usuario = db.session.execute(db.select(Usuario).filter_by(id=id)).scalar_one()
        usuario.nombreUsuario = request.form['nombreUsuario']
        usuario.contrasena = request.form['contrasena']
        usuario.nombreCompleto = request.form['nombreCompleto']
        usuario.rol = request.form['rol']
        usuario.departamento = request.form['departamento']
        usuario.unidad = request.form['unidad']
        db.session.commit()
        flash("¡Usuario editado exitosamente!", 'primary')
        return redirect(url_for('adminCrudUsuarios'))
    usuario = db.session.execute(db.select(Usuario).filter_by(id=id)).scalar_one()
    return render_template('views/admin/editarUsuario.html', usuario=usuario)

#UPDATE SOLICITUD(Admin)
#Edit de solicitud que redirige a la vista de Admin
@app.route('/aedits/<int:idSolicitud>', methods=['GET','POST'])
@login_required
def Aedit_solicitud(idSolicitud):
    if request.method == 'POST':
        solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
        solicitud.numero = request.form['numero']
        solicitud.fechaDeIngreso = request.form['fechaDeIngreso']
        solicitud.fechaDeVencimiento = request.form['fechaDeVencimiento']
        solicitud.nombreSolicitante = request.form['nombreSolicitante']
        solicitud.materia = request.form['materia']
        solicitud.tipo = request.form['tipo']
        solicitud.departamento = request.form['departamento']
        solicitud.usuarioID = request.form['funcionario']
        db.session.commit()
        return redirect(url_for('adminCrudSolicitudes'))
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    return render_template('views/editarSolicitud.html',solicitud=solicitud)


#UPDATE SOLICITUD(OIRS)
#Edit de solicitud que redirige a la vista de OIRS
@app.route('/oedits/<int:idSolicitud>', methods=['GET','POST']) 
@login_required
def Oedit_solicitud(idSolicitud):
    if request.method == 'POST':
        solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
        solicitud.numero = request.form['numero']
        solicitud.fechaDeIngreso = request.form['fechaDeIngreso']
        solicitud.fechaDeVencimiento = request.form['fechaDeVencimiento']
        solicitud.nombreSolicitante = request.form['nombreSolicitante']
        solicitud.materia = request.form['materia']
        solicitud.tipo = request.form['tipo']
        solicitud.departamento = request.form['departamento']
        solicitud.usuarioID = request.form['funcionario']
        db.session.commit()
        return redirect(url_for('oirsCrudSolicitudes'))
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    return render_template('views/editarSolicitud.html',solicitud=solicitud)


###   DELETES   ###
#DELETE SOLICITUD(Admin)
@app.route('/adeletes/<int:idSolicitud>')
@login_required
def adeletes(idSolicitud):
    estado = Estado.query.filter_by(fkIdSolicitud=idSolicitud).first()
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    if estado == None:
        db.session.delete(solicitud)
        db.session.commit()
        flash("¡Solcitiud eliminada exitosamente!",'warning')
    else:
        db.session.delete(solicitud)
        db.session.delete(estado)
        db.session.commit()
        flash("¡Solcitiud eliminada exitosamente!",'warning')
    solicitudes = get_solicitudes()
    return redirect(url_for('adminCrudSolicitudes', solicitudes=solicitudes))

#DELETE SOLICITUD(Oirs)
@app.route('/odeletes/<int:idSolicitud>')
@login_required
def odeletes(idSolicitud):
    estado = Estado.query.filter_by(fkIdSolicitud=idSolicitud).first()
    solicitud = db.session.execute(db.select(Solicitud).filter_by(idSolicitud=idSolicitud)).scalar_one()
    if estado == None:
        db.session.delete(solicitud)
        db.session.commit()
        flash("¡Solicitud eliminada exitosamente!",'warning')
    else:
        db.session.delete(solicitud)
        db.session.delete(estado)
        db.session.commit()
        flash("¡Solicitud eliminada exitosamente!",'warning')
    solicitudes = get_solicitudes()
    return redirect(url_for('oirsCrudSolicitudes', solicitudes=solicitudes))

#DELETE USUARIO
@app.route('/deleteu/<int:id>')
@login_required
def delete_usuario(id):
    usuario = db.session.execute(db.select(Usuario).filter_by(id=id)).scalar_one()
    db.session.delete(usuario)
    db.session.commit()
    flash("¡Usuario eliminado exitosamente!",'danger')
    usuarios = get_users()
    return redirect(url_for('adminCrudUsuarios', usuarios=usuarios))

if __name__ == '__main__':
    app.config.from_object(config['development'])
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')