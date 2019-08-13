# Packages
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import scipy.io as sio
from scipy.linalg import eig, sqrtm, inv
import pdb
import os


def cjade(X, m=None, max_iter=200):
    """ Source separation of complex signals with JADE.
    Jade performs `Source Separation' in the following sense:
      X is an n x T data matrix assumed modelled as X = A S + N where

    o A is an unknown n x m matrix with full rank.
    o S is a m x T data matrix (source signals) with the properties
         a) for each t, the components of S(:,t) are statistically
            independent
      b) for each p, the S[p,:] is the realization of a zero-mean
         `source signal'.
      c) At most one of these processes has a vanishing 4th-order
        cumulant.
    o  N is a n x T matrix. It is a realization of a spatially white
       Gaussian noise, i.e. Cov(X) = sigma*eye(n) with unknown variance
       sigma.  This is probably better than no modeling at all...

    Jade performs source separation via a
    Joint Approximate Diagonalization of Eigen-matrices.

    THIS VERSION ASSUMES ZERO-MEAN SIGNALS

    Input :
      * X: Each column of X is a sample from the n sensors (time series' in rows)
      * m: m is an optional argument for the number of sources.
        If ommited, JADE assumes as many sources as sensors.

    Output :
       * A is an n x m estimate of the mixing matrix
       * S is an m x T naive (ie pinv(A)*X)  estimate of the source signals
    """

    # Version 1.6.  Copyright: JF Cardoso.  
    # Translated to Python by Michael A. Casey, Bregman Labs, All Rights Reserved
    # See notes, references and revision history at the bottom of this file



    # Copyright (c) 2013, Jean-Francois Cardoso
    # All rights reserved.
    #
    #
    # BSD-like license.
    # Redistribution and use in source and binary forms, with or without modification, 
    # are permitted provided that the following conditions are met:
    #
    # Redistributions of source code must retain the above copyright notice, 
    # this list of conditions and the following disclaimer.
    #
    # Redistributions in binary form must reproduce the above copyright notice,
    # this list of conditions and the following disclaimer in the documentation 
    # and/or other materials provided with the distribution.
    #
    #
    # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS 
    # OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    # AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER 
    # OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    # DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
    # DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER 
    # IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
    # OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    if not isinstance(X, np.matrixlib.defmatrix.matrix):
        X = np.matrix(X, dtype=np.complex_)
    n, T = X.shape

    #  source detection not implemented yet !
    m = n if m is None else m

    #############################################################
    # A few parameters that could be adjusted
    nem = m  # number of eigen-matrices to be diagonalized
    seuil = 1/np.sqrt(T)/100.  # a statistical threshold for stopping joint diag

    if m < n:  # assumes white noise
            D, U = eig((X*X.H)/T)
            k = np.argsort(D)
            puiss = D[k]
            ibl = np.sqrt(puiss[n-m:n]-puiss[:n-m].mean())
            bl = np.ones((m, 1), dtype=np.complex_) / ibl
            W = np.diag(np.diag(bl))*np.matrix(U[:n, k[n-m:n]]).H
            IW = np.matrix(U[:n, k[n-m:n]])*np.diag(ibl)
    else:    # assumes no noise
            IW = sqrtm((X*X.H)/T)
            W = inv(IW)
    Y = W * X

    # Cumulant estimation
    R = (Y*Y.H)/T
    C = (Y*Y.T)/T

    czeros = lambda dim: np.matrix(np.zeros(dim, dtype=np.complex_))  # Initialize complex matrices
    ceye = lambda sz: np.matrix(np.eye(sz, dtype=np.complex_))

    Yl = czeros((1, T))
    Ykl = czeros((1, T))
    Yjkl = czeros((1, T))

    Q = czeros((m*m*m*m, 1))
    index = 0

    for lx in np.arange(m):
        Yl = Y[lx, :]
        for kx in np.arange(m):
            Ykl = np.multiply(Yl, Y[kx, :].conj())  # element-wise multiply
            for jx in np.arange(m):
                Yjkl = np.multiply(Ykl, Y[jx, :].conj())
                for ix in np.arange(m):
                    Q[index] = (Yjkl*Y[ix, :].T)/T - R[ix, jx]*R[lx, kx] - R[ix, kx]*R[lx, jx] - C[ix, lx]*C[jx, kx].conj()
                    index += 1

    # If you prefer to use more memory and less CPU, you may prefer this
    # code (due to J. Galy of ENSICA) for the estimation the cumulants
    # ones_m = ones(m,1) ;
    # T1 = kron(ones_m,Y);
    # T2 = kron(Y,ones_m);
    # TT = (T1.* conj(T2)) ;
    # TS = (T1 * T2.')/T ;
    # R = (Y*Y')/T  ;
    # Q = (TT*TT')/T - kron(R,ones(m)).*kron(ones(m),conj(R)) - R(:)*R(:)' - TS.*TS'



    ############################################################
    # computation and reshaping of the significant eigen matrices

    D, U = eig(Q.reshape(m*m, m*m))
    la = np.absolute(D)  # la = np.absolute(np.diag(D))
    K = np.argsort(la)
    la = la[K]

    # reshaping the most (there are `nem' of them) significant eigenmatrice
    M = czeros((m, nem*m))  # array to hold the significant eigen-matrices
    Z = czeros((m, m))  # buffer
    h = m*m - 1
    for u in np.arange(0, nem*m, m): 
        Z[:] = U[:, K[h]].reshape(m, m)
        M[:, u:u+m] = la[h]*Z
        h -= 1

    ############################################################
    # joint approximate diagonalization of the eigen-matrices

    # Better declare the variables used in the loop :
    B = np.matrix([[1, 0, 0], [0, 1, 1], [0, -1j, 1j]])
    Bt = B.H
    Ip = czeros((1, nem))
    Iq = czeros((1, nem))
    g = czeros((3, nem))
    G = czeros((2, 2))
    vcp = czeros((3, 3))
    D = czeros((3, 3))
    la = czeros((3, 1))
    K = czeros((3, 3))
    angles = czeros((3, 1))
    pair = czeros((1, 2))
    c = 0 
    s = 0 

    # init
    V = ceye(m)

    # Main loop
    encore = True
    n_iter = 0
    while encore and n_iter < max_iter:
        encore = False
        n_iter += 1
        for p in np.arange(m-1):
            for q in np.arange(p+1, m):
                Ip = np.arange(p, nem*m, m)
                Iq = np.arange(q, nem*m, m)

                # Computing the Givens angles
                g = np.r_[M[p, Ip]-M[q, Iq], M[p, Iq], M[q, Ip]]
                D, vcp = eig((B*(g*g.H)*Bt).real)
                K = np.argsort(D)  # K = np.argsort(diag(D))
                la = D[K]  # la = diag(D)[k]
                angles = vcp[:, K[2]]
                angles = -angles if angles[0] < 0 else angles
                c = np.sqrt(0.5+angles[0]/2.0)
                s = 0.5*(angles[1]-1j*angles[2])/c
                if np.absolute(s) > seuil:  # updates matrices M and V by a Givens rotation
                    encore = True
                    pair = np.r_[p, q]
                    G = np.matrix(np.r_[np.c_[c, -np.conj(s)], np.c_[s, c]])
                    V[:, pair] = V[:, pair] * G
                    M[pair, :] = G.H * M[pair, :]
                    M[:, np.r_[Ip, Iq]] = np.c_[c*M[:, Ip]+s*M[:, Iq], -np.conj(s)*M[:, Ip]+c*M[:, Iq]]

    # estimation of the mixing matrix and signal separation
    A = IW*V
    S = V.H*Y

    return A, S


def create_folder(directory):
    """ Creates folders in the current directory called S1, S2, Recovered_S1, and Recovered_S2 """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print('Error: Creating directory. ' + directory)


def time_to_sample(args):
    """ Converts the time to the exact sample"""
    return args*50000


def main():

    create_folder('./S1/')
    create_folder('./S2/')
    create_folder('./Recovered_S2/')
    create_folder('./Recovered_S1/')

    # Gather the Data
    data = sio.loadmat('data.mat')
    X = data['data'][1:13, :]

    # Perform JADE to get the recovered signals array (Y) and the adjancency matrix (A)
    A, Y = cjade(X, m=12, max_iter=200)

    # # Plot the data
    # plt.plot(data['alldata'][0, 0:41095].T,Y[4:12, 0:41095].T)
    # plt.plot(data['alldata'][0, 0:41095].T,data['alldata'][4:12, 0:41095].T)

    # Constants
    offset = 0.14

    # The start of the heart cycle, roughly 0.8 seconds,
    # but we are counting from where S1 begins
    time_range = np.arange(offset, 16.00, 0.680)
    sample_range = time_to_sample(time_range)

    # Set where S1 and S2 Start
    beg_s1 = time_range + 0.03
    end_s1 = beg_s1 + 0.1
    beg_s2 = beg_s1 + 0.27
    end_s2 = beg_s2 + 0.06

    # Get their appropriate samples
    sample_s1_beg, sample_s1_end = time_to_sample(beg_s1), time_to_sample(end_s1)
    sample_s2_beg, sample_s2_end = time_to_sample(beg_s2), time_to_sample(end_s2)

    # Create a List of where the S1 and S2 samples begin and end
    B = list(zip(sample_s1_beg, sample_s1_end))
    C = list(zip(sample_s2_beg, sample_s2_end))

    # Pre-allocate Array space for S1 (Space could either be 5000 or 4999)
    s1_1, s1_2 = np.empty([len(X), 5000]), np.empty([len(X), 4999])

    # Sometimes S1 is complex
    s1_recovered1, s1_recovered2 = np.empty([len(X), 5000], dtype=np.complex128), \
                                   np.empty([len(X), 4999], dtype=np.complex128)

    # Pre-allocate Array space for S2
    # Space could either be 3000 or 3001
    s2_1, s2_2 = np.empty([len(X), 3000]), np.empty([len(X), 3001])
    s2_recovered1, s2_recovered2 = np.empty([len(X), 3000], dtype=np.complex128), \
                                   np.empty([len(X), 3001], dtype=np.complex128)

    results_1, results_2 = False, False

    # For S1 and Recovered_S1
    for i, item in enumerate(B):  # 24 cycles (0.680 seconds)
        for j in range(len(X)):  # all mics

            # Check if we have reached 5000 samples
            if len(data['data'][j, int(B[i][0])-1:int(B[i][1])-1]) == 5000 and \
                    Y[j, int(B[i][0])-1:int(B[i][1])-1].shape[-1] == 5000:

                # Place in S1 or S1_covered array
                s1_1[j] = data['data'][j, int(B[i][0])-1:int(B[i][1])-1]
                s1_recovered1[j] = Y[j, int(B[i][0])-1:int(B[i][1])-1]
            else:
                # Otherwise, if there are 4999 samples, place in the other array
                s1_2[j] = data['data'][j, int(B[i][0])-1:int(B[i][1])-1]
                s1_recovered2[j] = Y[j, int(B[i][0])-1:int(B[i][1])-1]

                # Set the boolean flag
                results_1 = True
        s1_filename = './S1/S1_Cycle'+str(i)+'.mat'
        s1_recovered_filename = './Recovered_S1/S1_Cycle'+str(i)+'.mat'

        # If the flag is true, save the specific array size
        if results_1:
            sio.savemat(s1_filename, {'S1': s1_2})
            sio.savemat(s1_recovered_filename, {'S1': s1_recovered2})
        else:
            sio.savemat(s1_filename, {'S1': s1_1})
            sio.savemat(s1_recovered_filename, {'S1': s1_recovered1})

    # For S2 and Recovered S2
    for i, item in enumerate(C):
        for j in range(len(X)):
            if len(data['data'][j, int(C[i][0])-1:int(C[i][1])-1]) == 3000 and \
                    Y[j, int(C[i][0])-1:int(C[i][1])-1].shape[-1] == 3000:
                s2_1[j] = data['data'][j, int(C[i][0])-1:int(C[i][1])-1]
                s2_recovered1[j] = Y[j, int(C[i][0])-1:int(C[i][1])-1]
            else:
                s2_2[j] = data['data'][j, int(C[i][0])-1:int(C[i][1])-1]
                s2_recovered2[j] = Y[j, int(C[i][0])-1:int(C[i][1])-1]
                results_2 = True

        s2_recovered_filename = './Recovered_S2/S2_Cycle'+str(i)+'.mat'
        s2_filename = './S2/S2_Cycle'+str(i)+'.mat'
        if results_2:
            sio.savemat(s2_filename, {'S2': s2_2})
            sio.savemat(s2_recovered_filename, {'S2': s2_recovered2})
        else:
            sio.savemat(s2_filename, {'S2': s2_1})
            sio.savemat(s2_recovered_filename, {'S2': s2_recovered1})


if __name__ == '__main__':
    main()
