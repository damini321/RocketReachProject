from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import render, HttpResponse
from knox.models import AuthToken
from django.contrib.auth import login
from .serializers import UserSerializer, RegisterSerializer, AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from .serializers import *
from .models import *
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, ListAPIView, CreateAPIView
from django.contrib.auth.decorators import login_required
from rest_framework import status, viewsets, generics
from rest_framework.views import APIView
from space.errors import InsufficientTokens
from rest_framework.filters import SearchFilter
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from rest_framework.decorators import action

fs = FileSystemStorage(location='tmp/')

# Register API
class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })


class LoginAPI(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginAPI, self).post(request, format=None)


class UserProfileView(CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User_Profile.objects.all()
    serializer_class = ProfileSerializer

class UserView(CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = User.objects.all()
    serializer_class = UserSerializer

class Profile_list(generics.ListAPIView):
    queryset = User_Profile.objects.all().order_by("-created_at")
    serializer_class = ProfileSerializer
    filter_backends = [SearchFilter]
    search_fields = ['full_name', 'phone', 'DOB']



class Profile_Retrieve_View(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny, ]
    
    def retrieve(self, request, *args, **kwargs):
        if self.request.user:
            logged_in_user_query = User.objects.get(id=self.request.user.id)  # (id=self.kwargs["id"])
            #print(logged_in_user_query)
            if logged_in_user_query.tokens == 0:
                return redirect('http://127.0.0.1:8000/purchased_subcription_create/')
               # return Response({"error": "Token Expire, Go to subcription page!!"}, status=status.HTTP_401_UNAUTHORIZED)
            #elif logged_in_user_query.tokens <= 5:
            elif logged_in_user_query.tokens > 0:
                logged_in_user_query.tokens = logged_in_user_query.tokens - 1
                logged_in_user_query.save()
                try:
                    query = User.objects.get(id=self.kwargs["id"])  # id=self.request.user.id
                    serializer = self.get_serializer(query)
                    print(query)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except ObjectDoesNotExist:
                    return Response({"DOES_NOT_EXIST": "Does not exist"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"NO_ACCESS": "Access Denied"}, status=status.HTTP_401_UNAUTHORIZED)



class Pricing_Plan_List(generics.ListAPIView):
    queryset = Pricing_Plan.objects.all()
    serializer_class = PricingSerializer
    permission_classes = [AllowAny, ]

    def list(self, request, *args, **kwargs):
        if self.request.user:
            print(self.request.user)
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"NO_ACCESS": "Access Denied"}, status=status.HTTP_401_UNAUTHORIZED)    
            

class Purchased_Subcription_View(generics.CreateAPIView):
    queryset = Purchased_Subcription.objects.all()
    serializer_class = PurchasedSubcriptionSerializer

    def post(self, request, format=None):
        serializer = PurchasedSubcriptionSerializer(data=request.data)
       # print(serializer)
        
        if serializer.is_valid():
            serializer.save()
            #print(serializer.data)
            subscription  = serializer.data['subscription']
            #print(subscription)
            query = Pricing_Plan.objects.get(id=subscription)
            #query.tokens += subscription
            print(query.tokens)
            user=query.tokens
            #query.tokens += 1500
            #print(query)
            # query_user=User_Profile.objects.get(id=query)
            # print(query_user)
            user_name  = serializer.data['user_name']
            print(user_name)
            query_user=User.objects.get(id=user_name)
            print(query_user.tokens)
            query_user.tokens+=user
            # query_user.tokens +=1500
            query_user.save()
            
            
            #query_user.tokens += 1500
            print(query_user)

            # query = User_Profile.objects.get(id=user_name)# id=self.request.user.id
            # print(query.subscription)
            # serializer = self.get_serializer(query)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
   
def checkout(request,id):
    if request.method == "GET":
        return render(request, 'pay.html')
    try:    
        tokens = int(request.POST['token'])    
    except:
        return render(request, 'pay.html') 
        order = User_Profile.objects.create(tokens=tokens)
        order.save()
        merchant_key = settings.PAYTM_SECRET_KEY
        params = (
                ('MID', settings.PAYTM_MERCHANT_ID),
                ('ORDER_ID', str(order.order_id)),
                ('CUST_ID', 'test555666@paytm.com'),
                ('TXN_AMOUNT', str(order.tokens)),
                ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
                ('WEBSITE', settings.PAYTM_WEBSITE),
                ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
                ('CALLBACK_URL', 'http://127.0.0.1:8000/handlerequest/'),
        )
        paytm_params = dict(params)
        checksum = generate_checksum(paytm_params, merchant_key)
        order.checksum = checksum
        order = Add_Funds.objects.get(id=id)
        order.account_balance += enter_amount
        order.save()
        id = order.order_id
        paytm_params['CHECKSUMHASH'] = checksum
        print('SENT: ', checksum)
        return render(request, 'redirect.html', context=paytm_params)
    
@csrf_exempt
def handlerequest(request):
    queryset = Add_Funds.objects.all()
    serializer_class = Add_Funds_Serializer
    if request.method == 'POST':
        paytm_checksum = ''
        print(request.body)
        print(request.POST)
        received_data = dict(request.POST)
        print(received_data)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            print("Checksum Matched")
            received_data['message'] = "Checksum Matched"
        else:
            print("Checksum Mismatched")
            received_data['message'] = "Checksum Mismatched"

        return render(request, 'callback.html', context=received_data)
    

class ContactView(viewsets.ModelViewSet):
    
    queryset = Contacts.objects.all()
    serializer_class = ContactSerializer
    
    @action(detail=False, methods=['POST'])
    def upload_data(self, request):
        """Upload data from CSV"""
        file = request.FILES["file"]

        content = file.read()  # these are bytes
        file_content = ContentFile(content)
        file_name = fs.save("_tmp.csv", file_content)
        tmp_file = fs.path(file_name)
        csv_file = open(tmp_file, errors="ignore")
        reader = csv.reader(csv_file)
        print(reader)
        data = list(reader) 
        print(data)
        contact_list=[]
        contact_dict=[]
        for row in data:
          
            print(row)
            for i in row:
                print(i)
            
            
                obj = list(User_Profile.objects.filter(full_name=i).values())
                print(obj)
                for j in obj:
                    contact_list.append(
                        Contacts(
                            full_name=j['full_name'],
                            stream=j['stream'],
                            school=j['school'],
                            degree=j['degree'],
                            job_title=j['job_title'],
                            skills=j['skills'],
                            experiance=j['experiance'],
                            company=j['company'],
                            phone=j['phone'],
                            email=j['email'],
                            linkdin=j['linkdin'],
                            Twitter=j['Twitter'],
                            alt_phone=j['alt_phone'],
                            gender=j['gender'],
                            DOB=j['DOB'],
                            profile_photo=j['profile_photo'],
                            location=j['location'],
                            created_at=j['created_at'],
                            updated_at=j['updated_at']
                        )
                    )
                    contact_dict.append(j)
            obj1=(Contacts.objects.bulk_create(contact_list))
            
            return Response(contact_dict)
