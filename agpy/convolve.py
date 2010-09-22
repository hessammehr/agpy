import numpy

try:
    #print "Attempting to import scipy.  If you experience a bus error at this step, it is likely because of a bad scipy install"
    import scipy
    import scipy.fftpack
    fft2 = scipy.fftpack.fft2
    ifft2 = scipy.fftpack.ifft2
    from scipy.special import j1
except ImportError:
    fft2 = numpy.fft.fft2
    ifft2 = numpy.fft.ifft2

def convolve(im1,im2,pad=True,crop=True,return_fft=False,fftshift=True,kernel_number=1,
        ignore_nan=False,ignore_zeros=False,min_wt=1e-8):
    """
    Convolve two images.  Returns the larger image size.  Assumes image &
    kernel are centered

    *NOTE* Order matters when padding; the kernel should either be first or
    kernel_number should be set to 2.  

    Options:
    pad - Default on.  Zero-pad image to the nearest 2^n
    crop - Default on.  Return an image of the size of the largest input image.
        If the images are asymmetric in opposite directions, will return the largest 
        image in both directions.
    return_fft - Return the FFT instead of the convolution.  Useful for making PSDs.
    fftshift - If return_fft on, will shift & crop image to appropriate dimensions
    kernel_number - if specified, assumes that image # is the kernel, otherwise uses
                   the smaller of the two or the first if they are equal-sized
    ignore_nan - attempts to re-weight assuming NAN values are meant to be
                ignored, not treated as zero.  
    ignore_zeros - Ignore the zero-pad-created zeros.  Desirable if you have periodic
                   boundaries on a non-2^n grid
    min_wt - If ignoring nans/zeros, force all grid points with a weight less than this
             value to NAN (the weight of a grid point with *no* ignored neighbors is 1.0)
    """

    # NAN catching
    nanmask1 = im1!=im1
    nanmask2 = im2!=im2
    im1[nanmask1] = 0
    im2[nanmask2] = 0

    shape1 = im1.shape
    shape2 = im2.shape
    # find ideal size (power of 2) for fft.  Can add shapes because they are tuples
    if pad:
        fsize = 2**numpy.ceil(numpy.log2(numpy.max(shape1+shape2)))
        newshape = numpy.array([fsize,fsize])
    else:
        newshape = numpy.array([numpy.max([shape1[0],shape2[0]]),numpy.max([shape1[1],shape2[1]])]) #numpy.array(shape1)+numpy.array(shape2)
    centerx, centery = newshape/2.
    im1quarter1x, im1quarter1y = centerx - shape1[0]/2.,centery - shape1[1]/2.
    im1quarter3x, im1quarter3y = centerx + shape1[0]/2.,centery + shape1[1]/2.
    im2quarter1x, im2quarter1y = centerx - shape2[0]/2.,centery - shape2[1]/2.
    im2quarter3x, im2quarter3y = centerx + shape2[0]/2.,centery + shape2[1]/2.
    bigim1 = numpy.zeros(newshape,dtype=numpy.complex128)
    bigim2 = numpy.zeros(newshape,dtype=numpy.complex128)
    bigim1[im1quarter1x:im1quarter3x,im1quarter1y:im1quarter3y] = im1
    bigim2[im2quarter1x:im2quarter3x,im2quarter1y:im2quarter3y] = im2 
    imfft1 = fft2(bigim1)
    imfft2 = fft2(bigim2)
    fftmult = imfft1*imfft2
    if ignore_nan or ignore_zeros:
        bigimwt = numpy.ones(newshape,dtype=numpy.complex128)
        if ignore_zeros: bigimwt[:] = 0.0
        if shape1[0] > shape2[0] or kernel_number==2: 
            bigimwt[im1quarter1x:im1quarter3x,im1quarter1y:im1quarter3y] = 1.0-nanmask1*ignore_nan
            kern = imfft2
        else:
            bigimwt[im2quarter1x:im2quarter3x,im2quarter1y:im2quarter3y] = 1.0-nanmask2*ignore_nan
            kern = imfft1
        wtfft = fft2(bigimwt)
        wtfftmult = wtfft*kern
        wtfftsm   = ifft2(wtfftmult)
        pixel_weight = numpy.fft.fftshift(wtfftsm).real

    quarter1x = numpy.min([im1quarter1x,im2quarter1x])
    quarter3x = numpy.max([im1quarter3x,im2quarter3x])
    quarter1y = numpy.min([im1quarter1y,im2quarter1y])
    quarter3y = numpy.max([im1quarter3y,im2quarter3y])
    if return_fft: 
        if fftshift: # default on 
            if crop:
                return numpy.fft.fftshift(fftmult)[ quarter1x:quarter3x, quarter1y:quarter3y ]
            else:
                return numpy.fft.fftshift(fftmult)
        else:
            return fftmult

    if ignore_nan or ignore_zeros:
        rifft = numpy.fft.fftshift( ifft2( fftmult ) ) / pixel_weight
        rifft[pixel_weight < min_wt] = numpy.nan
    else:
        rifft = numpy.fft.fftshift( ifft2( fftmult ) ) 
    if crop:
        result = rifft[ quarter1x:quarter3x, quarter1y:quarter3y ].real
        return result
    else:
        return rifft.real

def smooth(image,kernelwidth=3,kerneltype='gaussian',trapslope=None,silent=True,interp_nan=False,**kwargs):
    """
    Returns a smoothed image using a gaussian, boxcar, or tophat kernel

    Options: 
    kerneltype - gaussian, boxcar, or tophat.  
        For a gaussian, uses a gaussian with sigma = kernelwidth (in pixels) out to 9-sigma
        A boxcar is a kernelwidth x kernelwidth square 
        A tophat is a flat circle with radius = kernelwidth
    """

    if kerneltype == 'gaussian':
        gp = 9 # gaussian precision in n_sigma
        if kernelwidth*gp < image.shape[0] and kernelwidth*gp < image.shape[1]:
            xx,yy = numpy.indices([numpy.ceil(kernelwidth*gp),numpy.ceil(kernelwidth*gp)])
            sz1,sz2 = kernelwidth*gp,kernelwidth*gp
        else:
            xx,yy = numpy.indices(image.shape)
            sz1,sz2 = image.shape
        rr = numpy.sqrt((xx-sz1/2.)**2+(yy-sz2/2.)**2)
        kernel = numpy.exp(-(rr**2)/(2*kernelwidth**2))
        kernel /= kernel.sum() #/ (kernelwidth**2 * (2*numpy.pi))
#        if kernelwidth != numpy.round(kernelwidth):
#            print "Rounding kernel width to %i pixels" % numpy.round(kernelwidth)
#            kernelwidth = numpy.round(kernelwidth)

    if kerneltype == 'boxcar':
        if not silent: print "Using boxcar kernel size %i" % numpy.ceil(kernelwidth)
        kernel = numpy.ones([numpy.ceil(kernelwidth),numpy.ceil(kernelwidth)],dtype='float64') / kernelwidth**2
    elif kerneltype == 'tophat':
        kernel = numpy.zeros(image.shape,dtype='float64')
        xx,yy = numpy.indices(image.shape)
        rr = numpy.sqrt((xx-image.shape[0]/2.)**2+(yy-image.shape[1]/2.)**2)
        kernel[rr<kernelwidth] = 1.0
        # normalize
        kernel /= kernel.sum()
    elif kerneltype == 'brickwall':
        if not silent: print "Smoothing with a %f airy function" % kernelwidth
        xx,yy = numpy.indices(image.shape)
        rr = numpy.sqrt((xx-image.shape[0]/2.)**2+(yy-image.shape[1]/2.)**2)
        # airy function is first bessel(x) / x  [like the sinc]
        kernel = j1(rr/kernelwidth) / (rr/kernelwidth) 
        # fix NAN @ center
        kernel[rr==0] = 0.5
        # normalize - technically, this should work, but practically, flux is GAINED in some images.  
        kernel /= kernel.sum()
    elif kerneltype == 'trapezoid':
        if trapslope:
            xx,yy = numpy.indices(image.shape)
            rr = numpy.sqrt((xx-image.shape[0]/2.)**2+(yy-image.shape[1]/2.)**2)
            zz = rr.max()-(rr*trapslope)
            zz[zz<0] = 0
            zz[rr<kernelwidth] = 1.0
            kernel = zz/zz.sum()
        else:
            if not silent: print "trapezoid function requires a slope"

    bad = (image != image)
    temp = image.copy()
    # convolve does this already temp[bad] = 0
    temp = convolve(temp,kernel,kernel_number=2,ignore_nan=interp_nan,**kwargs)
    if interp_nan is False: temp[bad] = image[bad]

    return temp

