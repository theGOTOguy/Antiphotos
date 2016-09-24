# Antiphotos
Photo-processing tool in Python to produce synthetic long exposures and antiphotos.

## Getting Started

### Photos

Good candidates for antiphotos are taken from a tripod with a timer using a constant ISO, a constant shutter speed, and manual focus.
This repository includes some suitable photos for you to experiment with.  Photos should be taken in RAW format, as compression
noise will be a significant problem in this pixel-by-pixel processing tool.

### Converting

Photos should be converted over to a lossless format like TIFF before processing.  In Ubuntu, you can use ufraw-batch to do this:

`sudo apt-get install ufraw-batch`
`ufraw-batch --out-type=tiff *.ARW`

## Using antiphoto.py

Antiphoto.py is able to create both solargraphs and antiphotos.  In a solargraph, all of the pixel values are added up then normalized.
In an antiphoto, all of the pixel values where the value changed sufficiently are added up, then normalized.

For example:

`./antigraph7.py *.tif --output out/anti.tif --cutoff 10 --brighten 0.1 --unalias 1 --unshift 1 --threads 7`

Will run the algorithm against all of the tiff files in the current directory, in numerical order.  The options do the following:

--output out/anti.tif: The result will be stored in out/anti.tif
--cutoff 10: All pixels whose RGB value didn't change by at least 10 will be ignored.  Setting this to 0 will make solargraphs instead of antiphotos.
--brighten 0.1:  The top 0.1% of pixels will be at the brightest RGB value.
--unalias 1:  A pixel will not count as changed unless all pixels in a radius of 1 around it also changed.  This removes hot pixels.
--unshift 1:  A pixel will also be checked against pixels in a radius of 1 around it, to see if the photo might have shifted slightly.
--threads 7:  Processing will happen simultaneously on 7 threads.

## Try it!

You can find some appropriate images to experiment with [in Google Drive here.](https://drive.google.com/file/d/0B67qmvk4E9ZzUHhKdzdwXzFxVnc/view?usp=sharing)

First, unzip the samples.zip file in a subdirectory named "examples":

`mkdir examples`

`cd examples`

`unzip samples.zip`

Next, you'll need to convert the ARW files into TIFF files.

`ufraw-batch --out-path=example example/*.ARW --out-type=tiff`

### A solargraph

Now, let's try making a solargraph from the examples by setting the "cutoff" to zero:

`./antigraph.py example/*.tif --output solar.tif --cutoff 0 --brighten 0.1 --threads 7`

This may take a very long time to run, even hours depending on your PC.  You can confirm that it's still working using

`top`

in Linux.  You should see each thread working, likely using a lot of memory and CPU.

Notice that in the final result, the little fish have disappeared from the photo, and only the streambed is visible.
The little fish were averaged away in the synthetic long exposure.

### An antiphoto

Finally, let's try making an antiphoto:

`./antigraph.py example/*.tif --output anti.tif --cutoff 30 --brighten 0.1 --threads 7 --unshift 1 --unalias 2`

Again, this takes a while.  The final result is pretty striking in my opinion:  a constellation of little fish,
showing us different kind of swirling river:  one where only the fish's favorite part of the river is shown!
