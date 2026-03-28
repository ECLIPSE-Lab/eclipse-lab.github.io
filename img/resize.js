const Jimp = require('jimp');

const files = [
  'lecturecard_MG.jpg',
  'lecturecard_ML-PC.jpg',
  'lecturecard_MF-AIML.jpg'
];

async function processImages() {
  for (let file of files) {
    try {
      console.log(`Processing ${file}...`);
      const image = await Jimp.read(file);
      
      // The images might not be pure black on the edges, they might be #101010
      // autocrop uses a tolerance. 0.05 is a 5% tolerance for different near-black shades
      image.autocrop(0.05, false);
      
      // Let's also crop a predefined 15% margin off the top/bottom and sides 
      // just in case autocrop fails to detect the glowing gradient edge as "background"
      const w = image.bitmap.width;
      const h = image.bitmap.height;
      
      // Crop 10% off each side
      const cropX = Math.floor(w * 0.1);
      const cropY = Math.floor(h * 0.1);
      const cropW = Math.floor(w * 0.8);
      const cropH = Math.floor(h * 0.8);
      
      image.crop(cropX, cropY, cropW, cropH);

      // The user said "they are too large anyway", resize down to 800px width
      if (image.bitmap.width > 800) {
        image.resize(800, Jimp.AUTO);
      }
      
      await image.writeAsync(file);
      console.log(`Successfully cropped and resized ${file}`);
    } catch (err) {
      console.error(`Error processing ${file}:`, err);
    }
  }
}

processImages();
