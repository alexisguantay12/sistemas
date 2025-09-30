
from django.db import models
from django.contrib.auth.models import User


class Prestacion(models.Model):
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50, blank=True, null=True)  # si usás nomenclador
    precio = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


class Presupuesto(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('concretado', 'Concretado'),
        ('no_concretado', 'No Concretado'),
    ]

    # Datos del paciente
    paciente_nombre = models.CharField(max_length=200)
    paciente_dni = models.CharField(max_length=20, blank=True, null=True)
    paciente_edad = models.PositiveIntegerField(blank=True, null=True)
    paciente_direccion = models.CharField(max_length=255, blank=True, null=True)
    paciente_telefono = models.CharField(max_length=50, blank=True, null=True)
    obra_social = models.CharField(max_length=100, blank=True, null=True)

    # Datos médicos
    medico = models.CharField(max_length=200, blank=True, null=True)
    diagnostico = models.CharField(max_length=255, blank=True, null=True)

    # Seguimiento
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    motivo_no_concretado = models.TextField(blank=True, null=True)

    # Usuario que lo cargó 

    def total(self):
        return sum([item.subtotal() for item in self.items.all()])

    def __str__(self):
        return f"Presupuesto {self.id} - {self.paciente_nombre}"


class PresupuestoItem(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, related_name='items', on_delete=models.CASCADE)
    prestacion = models.ForeignKey(Prestacion, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)

    def subtotal(self):
        return self.prestacion.precio * self.cantidad

    def __str__(self):
        return f"{self.prestacion.nombre} x{self.cantidad}"
