# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status

class VideoUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        video = request.FILES.get('video')
        if video:
            print("done1")
            return Response({'message': 'Video uploaded'}, status=status.HTTP_201_CREATED)
        return Response({'error': 'No video uploaded'}, status=status.HTTP_400_BAD_REQUEST)