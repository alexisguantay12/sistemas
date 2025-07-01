from django.db import models
from applications.core.models import BaseAbstractWithUser

class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)  # O ForeignKey a User si tenés usuarios cargados
    
    def __str__(self):
        return self.nombre


class Terminal(BaseAbstractWithUser):
    ESTADO_CHOICES = [
        ('BUENA', 'Buena'),
        ('NUEVA', 'Nueva'),
        ('DEFECTUOSA', 'Defectuosa'),
    ]
    nombre = models.CharField(max_length=100,unique=True)
    mac = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES)
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
    ESTADO_CHOICES = [
        ('BUENO', 'Buenas'),
        ('NUEVO', 'Nueva'),
        ('DEFECTUOSO', 'Defectuosa'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField(max_length=100, blank=True) 
    descripcion = models.TextField(blank=True)
    nro_serie = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=50, default='Activo')
    
    terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.marca} {self.modelo}"


class Impresora(BaseAbstractWithUser):
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    nro_serie = models.CharField(max_length=100, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.marca})"


class MovimientoComponente(BaseAbstractWithUser):
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE)
    origen = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, related_name='origen_componente')
    destino = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, related_name='destino_componente')
    fecha = models.DateTimeField(auto_now_add=True) 
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.componente} - {self.fecha}"
