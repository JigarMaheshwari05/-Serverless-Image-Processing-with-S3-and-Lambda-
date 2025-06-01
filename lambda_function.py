import boto3
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS S3 client
s3 = boto3.client('s3')

# Bucket names
RAW_BUCKET = 'rawimagestore'
PROCESSED_BUCKET = 'processimagestore'

# Watermark configuration
WATERMARK_TEXT = '© MyWatermark - Mandalorian'
WATERMARK_POSITION = (10, 10)  # Top-left corner
RESIZE_SIZE = (800, 800)

def resize_image(image):
    return image.resize(RESIZE_SIZE)

def add_watermark(image):
    # Ensure image is RGBA (to preserve transparency)
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    try:
        font = ImageFont.load_default()
    except Exception as e:
        logger.warning(f"Could not load default font: {e}")
        font = None

    draw.text(WATERMARK_POSITION, WATERMARK_TEXT, fill=(255, 255, 255, 128), font=font)

    # Composite watermark onto image
    return Image.alpha_composite(image, watermark_layer)

def lambda_handler(event, context):
    logger.info("Lambda function triggered with event: %s", event)

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        logger.info(f"Received image {key} from bucket {bucket}")

        if bucket != RAW_BUCKET:
            logger.warning(f"Ignoring bucket {bucket}, expected {RAW_BUCKET}")
            continue

        try:
            # Get original image from S3
            response = s3.get_object(Bucket=RAW_BUCKET, Key=key)
            image_data = response['Body'].read()
            image = Image.open(BytesIO(image_data)).convert("RGBA")

            logger.info(f"Image {key} successfully read and opened.")

            # Resize and watermark
            resized = resize_image(image)
            watermarked = add_watermark(resized)

            # Save processed image
            buffer = BytesIO()
            watermarked.save(buffer, format='PNG')
            buffer.seek(0)

            # Upload to processed bucket
            s3.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=key,
                Body=buffer,
                ContentType='image/png'
            )

            logger.info(f"Image {key} successfully processed and uploaded to {PROCESSED_BUCKET}")

        except Exception as e:
            logger.error(f"Error processing image {key} from {bucket}: {str(e)}", exc_info=True)

    return {
        'statusCode': 200,
        'body': 'Image processed successfully.'
    }
