from django.contrib import admin
from .models import User_Profile, Pricing_Plan,Purchased_Subcription, User,Contacts

# Register your models here.

admin.site.register(User_Profile)
admin.site.register(Pricing_Plan)
admin.site.register(Purchased_Subcription)
admin.site.register(User)
admin.site.register(Contacts)