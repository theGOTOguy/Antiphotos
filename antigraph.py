#!/usr/bin/python

import argparse
import copy
import math
import multiprocessing
import Image
import threading

parser = argparse.ArgumentParser(
    description='Sums the differences between consecutive '
                'photos, subject to a cutoff.')

parser.add_argument(
    'filespec', type=str, nargs='+',
    help='Filespec for images to combine into an antigraph.')
parser.add_argument(
    '--output', type=str, nargs=1,
    help='Output file for completed antigraph.')
parser.add_argument(
    '--cutoff', type=int, nargs=1, default=[128],
    help='Threshold difference in order to be integrated. '
         '256 is the least sensitive value, rarely including any pixels. '
         '0 is the most sensitive value, which will make a solargraph '
         'including all pixels.')
parser.add_argument(
    '--brighten', type=float, nargs=1, default=[0.1],
    help='Brighten the image by adjusting the norm downward. '
         'This is a percentile between 0 and 100.')
parser.add_argument(
    '--unshift', type=int, nargs=1, default=[0],
    help='Even a camera stabilized by a tripod will shift slightly during '
         'an exposure, perhaps just by a few pixels.  This will cause '
         'stationary objects in frame to have halos.  This flag is the radius '
         'in pixels that will be checked for the minimum norm RGB delta.  '
         'This will somewhat blur the antigraph.')
parser.add_argument(
    '--threads', type=int, nargs=1, default=[1],
    help='The number of parallel threads to use during processing.')
parser.add_argument(
   '--unalias', type=int, nargs=1, default=[0],
   help='Do not count a pixel as changed unless all pixels in this radius '
        'also changed.')

args = parser.parse_args()

def abs_norm(vector):
  result = 0
  for x in vector:
    result += abs(x)
  return result

def sq_norm(vector):
  result = 0
  for x in vector:
    result += x * x
  return result

def get_mask(radius, size):
  return [
      [True if w * w + h * h <= radius * radius else False for w in range(size)]
      for h in range(size)]

def coord_in_bounds(w, h, max_w, max_h):
  return (w < max_w
          and h < max_h
          and w >= 0
          and h >= 0)

# For multithreading purposes.  Processes a set of files for the antigraph.
def process_antigraph(files, max_w, max_h, unshift, unalias, totals, cutoff):
  pxl = []
  last_pxl = []

  unshift_mask = get_mask(unshift, unshift + 1)
  unalias_mask = get_mask(unalias, unalias + 1)

  for f in files:
    last_pxl = pxl
    pxl = Image.open(f).load()

    if last_pxl:
      include_pixel = [[True for h in range(max_h)] for w in range(max_w)]

      # Because it is woefully inefficient to constantly be thrashing 
      # around arrays, we do the grace radius in the outermost loops.
      for w_grace in range(-1 * unshift, unshift + 1):
        for h_grace in range(-1 * unshift, unshift + 1):
          if unshift_mask[abs(w_grace)][abs(h_grace)]:
            for w in range(max_w):
              for h in range(max_h):
                w_coord = w + w_grace
                h_coord = h + h_grace
                if (coord_in_bounds(w_coord, h_coord, max_w, max_h)
                    and include_pixel[w_coord][h_coord]
                    and (sq_norm([pxl[w, h][0] - last_pxl[w_coord, h_coord][0],
                                  pxl[w, h][1] - last_pxl[w_coord, h_coord][1],
                                  pxl[w, h][2] - last_pxl[w_coord, h_coord][2]])
                         < cutoff)):
                  include_pixel[w][h] = False

      for w in range(max_w):
        for h in range(max_h):
          pixel_aliased = False
          for w_grace in range(-1 * unalias, unalias + 1):
            for h_grace in range(-1 * unalias, unalias + 1):
              w_coord = w + w_grace
              h_coord = h + h_grace

              if (not pixel_aliased
                  and coord_in_bounds(w_coord, h_coord, max_w, max_h)
                  and unalias_mask[abs(w_grace)][abs(h_grace)]
                  and not include_pixel[w_coord][h_coord]):
                pixel_aliased = True

          if not pixel_aliased:
            for rgb in range(3):
              totals[unroll_totals_index(w, h, max_h, rgb)] += pxl[w, h][rgb]

def unroll_totals_index(w, h, max_h, rgb):
  return w * 3 * max_h + h * 3 + rgb

# Get the maximum size for all images.
max_w = 0
max_h = 0
for f in args.filespec:
  im = Image.open(f)
  (w, h) = im.size

  max_w = max(max_w, w)
  max_h = max(max_h, h)

# Create an array to store the numeric totals for each pixel.
# This is a special multithreading thing--this Array will allow
# us to share memory between the threads.  Results are "rolled up"
# into a one-dimenisonal array.
totals = multiprocessing.Array('i', [0 for _ in range(3 * max_h * max_w)])

last_im = None
cutoff_squared = args.cutoff[0] * args.cutoff[0]  # Square for square norm.

# Process the antiphoto.
# This can take a long time so we can employ multiple threads.
num_files = len(args.filespec)

if num_files - 1 < args.threads[0]:
  args.threads[0] = num_files - 1

num_files_per_thread = math.ceil(num_files / args.threads[0]) 

for t in range(args.threads[0]):
  # We also need to do the first file in the next group, or we will have
  # fencepost problems
  files = args.filespec[int(t * num_files_per_thread):
                        int(min(((t + 1) * num_files_per_thread + 1), num_files))]

  threads = []
  thread = multiprocessing.Process(
      target=process_antigraph,
      args=(files, max_w, max_h, args.unshift[0], args.unalias[0], totals,
            cutoff_squared))
  thread.start()
  threads.append(thread)

# Wait for all threads to finish
for t in threads:
  t.join()

# Get the maximum norm value in totals, for normalization.
all_pxls = []
for w in range(max_w):
  for h in range(max_h):
    all_pxls.append(abs_norm([totals[unroll_totals_index(w, h, max_h, 0)],
                              totals[unroll_totals_index(w, h, max_h, 1)],
                              totals[unroll_totals_index(w, h, max_h, 2)]]))

all_pxls.sort()
renorm = all_pxls[int(float(len(all_pxls) - 1) * (100.0 - args.brighten[0]) / 100.0)]
renorm = max(renorm, 1)

master = Image.new("RGB", (max_w, max_h), "black")
for w in range(max_w):
  for h in range(max_h):
      master.putpixel(
          (w, h),
          tuple([min(255,
                 int(float(256) * float(totals[unroll_totals_index(w, h, max_h, rgb)]) / float(renorm)))
                 for rgb in range(3)]))

master.save(args.output[0])
