const AWS = require('aws-sdk');
const sharp = require('sharp');

const s3 = new AWS.S3();

const RAW_BUCKET = 'rawimagestore';       // Replace with your raw image bucket name
const PROCESSED_BUCKET = 'processimagestore'; // Replace with your processed image bucket name

exports.handler = async (event) => {
  try {
    // Get the object key from the event (triggered by S3 upload)
    const key = event.Records[0].s3.object.key;

    // 1. Download the image from raw bucket
    const rawImage = await s3.getObject({
      Bucket: RAW_BUCKET,
      Key: key
    }).promise();

    // 2. Create the watermark SVG text (large size, transparent background)
    const watermarkText = 'mandalorian';
    const svgWidth = 800;
    const svgHeight = 200;
    const fontSize = 120;

    const svgText = `
      <svg width="${svgWidth}" height="${svgHeight}">
        <style>
          .title { fill: rgba(255, 255, 255, 0.5); font-size: ${fontSize}px; font-weight: bold; font-family: Arial, sans-serif; }
        </style>
        <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" class="title">${watermarkText}</text>
      </svg>
    `;

    // 3. Use Sharp to composite watermark SVG on original image at bottom right corner
    const processedImageBuffer = await sharp(rawImage.Body)
      .composite([{
        input: Buffer.from(svgText),
        gravity: 'southeast',   // places watermark at bottom right
        blend: 'overlay'
      }])
      .toBuffer();

    // 4. Upload processed image to processed bucket
    await s3.putObject({
      Bucket: PROCESSED_BUCKET,
      Key: key,  // same key, can change if you want
      Body: processedImageBuffer,
      ContentType: rawImage.ContentType
    }).promise();

    console.log(`Successfully added watermark and uploaded to ${PROCESSED_BUCKET}/${key}`);

    return {
      statusCode: 200,
      body: 'Watermark added successfully.'
    };

  } catch (error) {
    console.error('Error processing image:', error);
    throw error;
  }
};
