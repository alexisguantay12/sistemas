from django.db import models
from applications.core.models import BaseAbstractWithUser
from django.utils import timezone

class Sector(models.Model):
    nombre = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)  # O ForeignKey a User si tenés usuarios cargados
    def __str__(self):
        return self.nombre


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return self.nombre


class Terminal(BaseAbstractWithUser):
    nombre = models.CharField(max_length=100,unique=True)
    mac = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=50)
    def __str__(self):
        return self.nombre


class Componente(BaseAbstractWithUser):
    TIPO_CHOICES = [
        ('RAM', 'Memoria RAM'),
        ('DISCO', 'Disco'),
        ('TECLADO', 'Teclado'),
        ('MONITOR', 'Monitor'),
        ('MOUSE', 'Mouse'),
        ('CPU', 'CPU'),
        ('OTRO', 'Otro'),
    ] 

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField(max_length=100, blank=True) 
    descripcion = models.TextField(blank=True)
    nro_serie = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=50)
    
    terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, blank=True,related_name='componentes')

    def __str__(self):
        return f"{self.tipo} - {self.marca} {self.modelo}"


class ComponenteStock(BaseAbstractWithUser):
    TIPO_CHOICES = [
        ('RAM', 'Memoria RAM'),
        ('DISCO', 'Disco'),
        ('MOTHERBOARD', 'Placa Madre'),
        ('TECLADO', 'Teclado'),
        ('MONITOR', 'Monitor'),
        ('MOUSE', 'Mouse'),
        ('CPU', 'CPU'),
        ('ROUTER', 'Router'),
        ('SWITCH', 'Switch'),
        ('AP', 'Access Point'),
        ('VGA', 'Cable VGA'),
        ('HDMI', 'Cable HDMI'),
        ('ETHERNET', 'Cable Red'),
        ('OTRO', 'Otro'),
    ] 

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField(max_length=100, blank=True) 
    descripcion = models.TextField(blank=True)
    nro_serie = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=50)
    stock = models.IntegerField(default=1,null=True)

class Servidor(BaseAbstractWithUser): 
    hostname = models.CharField(max_length=100)
    ip = models.CharField(max_length=20, blank=True)
    mac = models.CharField(max_length=17, blank=True)
    sistema_operativo = models.CharField(max_length=100)
    version_so = models.CharField(max_length=50)
    rol_principal = models.CharField(max_length=100)
    estado = models.CharField(max_length=20)  
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True) 

    fecha_alta = models.DateField(auto_now_add=True)
    ultima_revision = models.DateField(null=True, blank=True)

    max_ram = models.IntegerField(null=True)
    max_disco = models.IntegerField(null= True)
    cantidad_puertos = models.IntegerField(null=True)
    # Archivos opcionales 

 

class MovimientoComponente(BaseAbstractWithUser):
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE)
    origen = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, related_name='origen_componente')
    destino = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, related_name='destino_componente')
    fecha = models.DateTimeField(auto_now_add=True) 
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.componente} - {self.fecha}"




class DispositivoPeriferico(BaseAbstractWithUser):
    TIPO_CHOICES = [
        ('IMPRESORA', 'Impresora'),
        ('ESCANER', 'Escáner'),
    ]

    ESTADO_CHOICES = [
        ('FUNCIONANDO', 'Funcionando'),
        ('EN_REPARACION', 'En reparación'),
        ('FUERA_DE_SERVICIO', 'Fuera de servicio'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100, blank=True)
    nro_serie = models.CharField(max_length=100, blank=True)
    conexion = models.CharField(max_length=50, blank=True, help_text="Ej: USB, Red, Wi-Fi")
    ip = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True)
    observaciones = models.TextField(blank=True)
    
    ultima_revision = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Periférico"
        verbose_name_plural = "Periféricos"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.marca} {self.modelo}"
