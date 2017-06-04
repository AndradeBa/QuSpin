from __future__ import print_function, division

# need linear algebra packages
import scipy.sparse.linalg as _sla
import scipy.linalg as _la
import numpy.linalg as _npla
import scipy.sparse as _sp
from scipy.special import binom, hyp2f1
import numpy as _np
from inspect import isgenerator as _isgenerator 

# needed for isinstance only
from ..operators import ishamiltonian as _ishamiltonian
from ..operators import hamiltonian as _hamiltonian
from ..basis import spin_basis_1d,photon_basis,isbasis,photon_Hspace_dim

import warnings


__all__ = ["ent_entropy", "diag_ensemble", "KL_div", "obs_vs_time", "ED_state_vs_time", "mean_level_spacing","project_operator"]



def ent_entropy(system_state,basis,chain_subsys=None,DM=False,svd_return_vec=[False,False,False],**_basis_kwargs):
	"""
	This function calculates the entanglement entropy of a lattice quantum subsystem based on the Singular Value Decomposition (svd). The entanglement entropy is NORMALISED by the size of the
	reduced subsystem. 

	RETURNS:	dictionary with keys:

	'Sent': entanglement entropy.

	'DM_chain_subsys': (optional) reduced density matrix of chain subsystem.

	'DM_other_subsys': (optional) reduced density matrix of the complement subsystem.

	'lmbda': (optional) svd singular values

	--- arguments ---

	system_state: (required) the state of the quantum system. Can be a:

				-- pure state [numpy array of shape (Ns,)].

				-- density matrix (DM) [numpy array of shape (Ns,Ns)].

				-- diagonal DM [dictionary {'V_rho': V_rho, 'rho_d': rho_d} containing the diagonal DM
					rho_d [numpy array of shape (Ns,)] and its eigenbasis in the columns of V_rho
					[numpy arary of shape (Ns,Ns)]. The keys CANNOT be chosen arbitrarily.].

				-- a collection of states [dictionary {'V_states':V_states}] containing the states
					in the columns of V_states [shape (Ns,Nvecs)]

	basis: (required) the basis used to build 'system_state'. Must be an instance of 'photon_basis',
				'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'. 

	chain_subsys: (optional) a list of lattice sites to specify the chain subsystem. Default is

				-- [0,1,...,N/2-1,N/2] for 'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'.

				-- [0,1,...,N-1,N] for 'photon_basis'.

	DM: (optional) String to enable the calculation of the reduced density matrix. Available options are

				-- 'chain_subsys': calculates the reduced DM of the subsystem 'chain_subsys' and
					returns it under the key 'DM_chain_subsys'.

				-- 'other_subsys': calculates the reduced DM of the complement of 'chain_subsys' and
					returns it under the key 'DM_other_subsys'.

				-- 'both': calculates and returns both density matrices as defined above.

				Default is 'False'. 	

	alpha: (optional) Renyi alpha parameter. Default is '1.0'. When alpha is different from unity,
				the _entropy keys have attached '_Renyi' to their label.

	density: (optional) if set to 'True', the entanglement _entropy is normalised by the size of the
				subsystem [i.e., by the length of 'chain_subsys']. Detault is 'False'.

	subsys_ordering: (optional) if set to 'True', 'chain_subsys' is being ordered. Default is 'True'.

	* `svd_return_vec`: (optional) list of three booleans to return the Singular Value Decomposition (svd) 
		  parameters:

		  * `[ . ,True, . ]` svd singular values.

		  * `[ . , . ,True]` and `[True, . , . ]` are depricated.

		  Default is ```[False,False,False]```.

	"""

	# initiate variables
	variables = ["Sent"]
	translate_dict={"Sent":"Sent_A"}

	if DM == 'chain_subsys':
		variables.append("DM_chain_subsys")
		_basis_kwargs["return_rdm"]="A"
		

	elif DM =='other_subsys':
		variables.append("DM_other_subsys")
		_basis_kwargs["return_rdm"]="B"
		translate_dict={"Sent":"Sent_B"}

	elif DM == 'both':
		variables.append("DM_chain_subsys")
		variables.append("DM_other_subsys")
		_basis_kwargs["return_rdm"]="both"

	elif DM and DM not in ['chain_subsys','other_subsys','both']:
		raise TypeError("Unexpected keyword argument for 'DM'!")

	if svd_return_vec[1]:
		variables.append('lmbda')
		_basis_kwargs["return_rdm_EVs"]=True


	### translate arguments
	if isinstance(system_state,dict):
		if "rho_d" in system_state and "V_rho" in system_state:
			V_rho = system_state["V_rho"]
			rho_d = system_state["rho_d"] 
			state = _np.einsum("ji,j,jk->ik",V_rho,rho_d,V_rho.conj())
		elif "V_states" in system_state:
			state=system_state['V_states']
			_basis_kwargs["enforce_pure"]=True
		else:
			raise ValueError("expecting dictionary with keys ['V_rho','rho_d'] or ['V_states']")
	else:
		state=system_state

	translate_dict.update({"DM_chain_subsys":'rdm_A',"DM_other_subsys":'rdm_B',"both":'both','lmbda':"p_A"})
	
	Sent = basis.ent_entropy(state,sub_sys_A=chain_subsys,**_basis_kwargs)
	



	# store variables to dictionary
	return_dict = {}
	for i in variables:
		j=translate_dict[i]
		if i == 'lmbda':
			return_dict[i] = _np.sqrt( Sent[j] )
		else:
			return_dict[i] = Sent[j]

	return_dict.update(Sent)

	return return_dict

def _ent_entropy(system_state,basis,chain_subsys=None,density=False,subsys_ordering=True,alpha=1.0,DM=False,svd_return_vec=[False,False,False]):
	"""
	This function calculates the entanglement entropy of a lattice quantum subsystem based on the Singular Value Decomposition (svd). The entanglement entropy is NORMALISED by the size of the
	reduced subsystem. 

	RETURNS:	dictionary with keys:

	'Sent': entanglement entropy.

	'DM_chain_subsys': (optional) reduced density matrix of chain subsystem.

	'DM_other_subsys': (optional) reduced density matrix of the complement subsystem.

	'U': (optional) svd U matrix

	'V': (optional) svd V matrix

	'lmbda': (optional) svd singular values

	--- arguments ---

	system_state: (required) the state of the quantum system. Can be a:

				-- pure state [numpy array of shape (Ns,)].

				-- density matrix (DM) [numpy array of shape (Ns,Ns)].

				-- diagonal DM [dictionary {'V_rho': V_rho, 'rho_d': rho_d} containing the diagonal DM
					rho_d [numpy array of shape (Ns,)] and its eigenbasis in the columns of V_rho
					[numpy arary of shape (Ns,Ns)]. The keys CANNOT be chosen arbitrarily.].

				-- a collection of states [dictionary {'V_states':V_states}] containing the states
					in the columns of V_states [shape (Ns,Nvecs)]

	basis: (required) the basis used to build 'system_state'. Must be an instance of 'photon_basis',
				'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'. 

	chain_subsys: (optional) a list of lattice sites to specify the chain subsystem. Default is

				-- [0,1,...,N/2-1,N/2] for 'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'.

				-- [0,1,...,N-1,N] for 'photon_basis'.

	DM: (optional) String to enable the calculation of the reduced density matrix. Available options are

				-- 'chain_subsys': calculates the reduced DM of the subsystem 'chain_subsys' and
					returns it under the key 'DM_chain_subsys'.

				-- 'other_subsys': calculates the reduced DM of the complement of 'chain_subsys' and
					returns it under the key 'DM_other_subsys'.

				-- 'both': calculates and returns both density matrices as defined above.

				Default is 'False'. 	

	alpha: (optional) Renyi alpha parameter. Default is '1.0'. When alpha is different from unity,
				the _entropy keys have attached '_Renyi' to their label.

	density: (optional) if set to 'True', the entanglement _entropy is normalised by the size of the
				subsystem [i.e., by the length of 'chain_subsys']. Detault is 'False'.

	subsys_ordering: (optional) if set to 'True', 'chain_subsys' is being ordered. Default is 'True'.

	svd_return_vec: (optional) list of three booleans to return Singular Value Decomposition (svd) 
				parameters:

				-- [True, . , . ] returns the svd matrix 'U'.

				-- [ . ,True, . ] returns the singular values 'lmbda'.

				-- [ . , . ,True] returns the svd matrix 'V'.

				Any combination of the above is possible. Default is [False,False,False].
	"""

	# initiate variables
	variables = ["Sent"]

	if DM=='chain_subsys':
		variables.append("DM_chain_subsys")
		if svd_return_vec[0]:
			variables.append('U')
	elif DM=='other_subsys':
		variables.append("DM_other_subsys")
		if svd_return_vec[2]:
			variables.append('V')
	elif DM=='both':
		variables.append("DM_chain_subsys")
		variables.append("DM_other_subsys")
		if svd_return_vec[0]:
			variables.append('U')
		if svd_return_vec[2]:
			variables.append('V')
	elif DM and DM not in ['chain_subsys','other_subsys','both']:
		raise TypeError("Unexpected keyword argument for 'DM'!")

	if svd_return_vec[1]:
		variables.append('lmbda')
	
	

	# calculate reshaped system_state
	v, rho_d, N_A = _reshape_as_subsys(system_state,basis,chain_subsys=chain_subsys,subsys_ordering=subsys_ordering)
	del system_state
	
	"""
	This function has room for improvement: if only DM is requested, it can be obtained by
	DM_chain_subsys = v[0].dot(v[0].T)
	DM_other_subsys = v[0].T.dot(v[0])
	so there's NO NEED for an SVD!!!
	"""

	if DM == False:
		if rho_d is not None and rho_d.shape!=(1,): # need DM for Sent of a mixed system_state
			U, lmbda, _ = _npla.svd(v, full_matrices=False)
			DM_chain_subsys = _np.einsum('n,nij,nj,nkj->ik',rho_d,U,lmbda**2,U.conj() )
			DM='chain_subsys'
		else:
			lmbda = _npla.svd(v.squeeze(), compute_uv=False)
	elif DM == 'chain_subsys':
		U, lmbda, _ = _npla.svd(v, full_matrices=False)
		if rho_d is not None:
			DM_chain_subsys = _np.einsum('n,nij,nj,nkj->ik',rho_d,U,lmbda**2,U.conj() )
		else:
			DM_chain_subsys = _np.einsum('nij,nj,nkj->nik',U,lmbda**2,U.conj() )
	elif DM == 'other_subsys':
		_, lmbda, V = _npla.svd(v, full_matrices=False)
		if rho_d is not None:
			DM_other_subsys = _np.einsum('n,nji,nj,njk->ik',rho_d,V.conj(),lmbda**2,V )
		else:
			DM_other_subsys = _np.einsum('nji,nj,njk->nik',V.conj(),lmbda**2,V )
	elif DM == 'both':
		U, lmbda, V = _npla.svd(v, full_matrices=False)
		if rho_d is not None:
			DM_chain_subsys = _np.einsum('n,nij,nj,nkj->ik',rho_d,U,lmbda**2,U.conj() )
			DM_other_subsys = _np.einsum('n,nji,nj,njk->ik',rho_d,V.conj(),lmbda**2,V )
		else:
			DM_chain_subsys = _np.einsum('nij,nj,nkj->nik',U,lmbda**2,U.conj() )
			DM_other_subsys = _np.einsum('nji,nj,njk->nik',V.conj(),lmbda**2,V )

	del v

	# calculate singular values of reduced DM and the corresponding probabilities
	if rho_d is not None and rho_d.shape!=(1,):
		# diagonalise reduced DM
		if DM in ['chain_subsys', 'both']:
			p = _npla.eigvalsh(DM_chain_subsys)
		elif DM == 'other_subsys':
			p = _npla.eigvalsh(DM_other_subsys)
			
		if svd_return_vec[1]: # if lmdas requested by user
			lmbda = _np.sqrt(abs(p))
	else:# calculate probabilities
		p = (lmbda**2.0).T
	
	# add floating point number to zero elements
	p[p<=1E-16] = _np.finfo(p.dtype).eps
		
	# calculate entanglement _entropy of 'system_state'
	if alpha == 1.0:
		Sent = -_np.sum( p*_np.log(p),axis=0).squeeze()
	else:
		Sent =  1.0/(1.0-alpha)*_np.log(_np.sum(p**alpha, axis=0)).squeeze()
	
	if density:
		Sent /= N_A

	# store variables to dictionar
	return_dict = {}
	for i in variables:
		return_dict[i] = vars()[i]

	return return_dict

def _reshape_as_subsys(system_state,basis,chain_subsys=None,subsys_ordering=True):
	"""
	This function reshapes an input state (or matrix with 'Nstates' initial states) into an array of
	the shape (Nstates,Ns_subsys,Ns_other) with 'Ns_subsys' and 'Ns_other' the Hilbert space dimensions
	of the subsystem and its complement, respectively.

	RETURNS:	reshaped state, 
				vector with eigenvalues of the DM associated with the initial state, 
				subsystem size

	--- arguments ---

	system_state: (required) the state of the quantum system. Can be a:

				-- pure state [numpy array of shape (1,) or (,1)].

				-- density matrix (DM) [numpy array of shape (1,1)].

				-- diagonal DM [dictionary {'V_rho': V_rho, 'rho_d': rho_d} containing the diagonal DM
					rho_d [numpy array of shape (1,) or (,1)] and its eigenbasis in the columns of V_rho
					[numpy arary of shape (1,1)]. The keys are CANNOT be chosen arbitrarily. 'rho_d'
					can be 'None', but needs to always be passed.

				-- a collection of states [dictionary {'V_states':V_states}] containing the states
					in the columns of V_states [shape (Ns,Nvecs)]

	basis: (required) the basis used to build 'system_state'. Must be an instance of 'photon_basis',
				'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'. 

	chain_subsys: (optional) a list of lattice sites to specify the chain subsystem. Default is

				-- [0,1,...,N/2-1,N/2] for 'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'.

				-- [0,1,...,N-1,N] for 'photon_basis'. 

	subsys_ordering: (optional) if set to 'True', 'chain_subsys' is being ordered. Default is 'True'. 
	"""

	try:
		N = basis.N
	except AttributeError:
		N = basis.particle_N



	if chain_subsys is not None:
		try:
			chain_subsys = [i for i in iter(chain_subsys)]
		except TypeError:
			raise TypeError("Expecting iterable for for 'chain_subsys'!")
		if len(chain_subsys) == 0:
			raise TypeError("Expecting a nonempty iterable for 'chain_subsys'!")
		elif min(chain_subsys) < 0:
			raise TypeError("'subsys' must be contain nonnegative numbers!")
		elif max(chain_subsys) > N-1:
			raise TypeError("'subsys' contains sites exceeding the total lattice site number!")
		elif len(set(chain_subsys)) < len(chain_subsys):
			raise TypeError("'subsys' cannot contain repeating site indices!")
		elif any(not _np.issubdtype(type(s),_np.integer) for s in chain_subsys):
			raise ValueError("'subsys' must iterable of integers with values in {0,...,L-1}!")
		elif subsys_ordering:
			if len(set(chain_subsys))==len(chain_subsys) and sorted(chain_subsys)!=chain_subsys:
				# if chain subsys is def with unordered sites, order them
				warnings.warn("'subsys' {} contains non-ordered sites. 'subsys' re-ordered! To change default set 'subsys_ordering = False'.".format(chain_subsys),stacklevel=4)
				chain_subsys = sorted(chain_subsys)

	
	if isinstance(system_state,dict):
		keys = set(system_state.keys())
		if keys == set(['V_rho','rho_d']):
			istate = 'DM'
			# define initial state
			rho_d = system_state['rho_d']
			if rho_d.shape != (basis.Ns,):
				raise ValueError("expecting a 1d array 'rho_d' of size {}!".format(basis.Ns))
			elif _np.any(rho_d < 0):
				raise ValueError("expecting positive eigenvalues for 'rho_d'!")
			psi = system_state['V_rho']
			if psi.shape != (basis.Ns,basis.Ns):
				raise ValueError("expecting a 2d array 'V_rho' of size ({},{})!".format(basis.Ns,basis.Ns))
		elif keys == set(['V_states']):
			istate = 'pure'
			rho_d = None
			psi = system_state['V_states']
		else:
			raise ValueError("expecting dictionary with keys ['V_rho','rho_d'] or ['V_states']")


		if _sp.issparse(system_state):
			warnings.warn("ent_entropy function only handles numpy.ndarrays, sparse matrix will be comverted to dense matrix.",UserWarning,stacklevel=4)
			system_state = system_state.todense()
			if system_state.shape[1] == 1:
				system_state = system_state.ravel()

		elif system_state.__class__ not in  [_np.ndarray,_np.matrix]:
			system_state = _np.asanyarray(system_state)


		if psi.ndim != 2:
			raise ValueError("Expecting ndim == 2 for V_states.")

		if psi.shape[0] != basis.Ns:
			raise ValueError("V_states shape {0} not compatible with basis size: {1}.".format(psi.shape,basis.Ns))
	else:
		if _sp.issparse(system_state):
			warnings.warn("ent_entropy function only handles numpy.ndarrays, sparse matrix will be comverted to dense matrix.",UserWarning,stacklevel=4)
			system_state = system_state.todense()
			if system_state.shape[1] == 1:
				system_state = system_state.ravel()
		elif system_state.__class__ not in  [_np.ndarray,_np.matrix]:
			system_state = _np.asanyarray(system_state)

			


		if system_state.ndim == 1: # pure state
			istate = 'pure'
			# define initial state
			psi = system_state
			rho_d = _np.reshape(1.0,(1,))
		elif system_state.ndim == 2: # DM
			if system_state.shape[0] != system_state.shape[1]:
				raise ValueError("Expecting square array for Density Matrix.")
			istate = 'DM'
			# diagonalise DM
			rho_d, psi = _la.eigh(system_state)
			if _np.min(rho_d) < 0 and abs(_np.min(rho_d)) > 1E3*_np.finfo(rho_d.dtype).eps:
				raise ValueError("Expecting DM to have positive spectrum")
			elif abs(1.0 - _np.sum(rho_d) ) > 1E3*_np.finfo(rho_d.dtype).eps:
				raise ValueError("Expecting eigenvalues of DM to sum to unity!")
			rho_d = abs(rho_d)

		if psi.shape[0] != basis.Ns:
			raise ValueError("V_states shape {0} not compatible with basis size: {1}.".format(psi.shape,basis.Ns))			
			


	# clear up memory
	del system_state


	# define number of participating states in 'system_state'
	Ns = psi[0,].size

	
	if basis.__class__.__name__[:-9] in ['spin','boson','fermion']:

		# set chain subsys if not defined
		if chain_subsys is None: 
			chain_subsys=list(i for i in range( N//2 ))
			warnings.warn("Subsystem contains sites {}.".format(chain_subsys),stacklevel=4)
		
	
		# re-write the state in the initial basis
		if basis.Ns<basis.sps**N:
			psi = basis.get_vec(psi,sparse=False)
			
		#calculate H-space dimensions of the subsystem and the system
		N_A = len(chain_subsys)
		Ns_A = basis.sps**N_A
		# define lattice indices putting the subsystem to the left
		system = chain_subsys[:]
		[system.append(i) for i in range(N) if not i in chain_subsys]
		print(system)
		'''
		the algorithm for the entanglement _entropy of an arbitrary subsystem goes as follows 
		for spin-1/2 and fermions [replace the onsite DOF (=2 below) with # states per site (basis.sps)]:

		1) the initial state psi has 2^N entries corresponding to the spin-z configs
		2) reshape psi into a 2x2x2x2x...x2 dimensional array (N products in total). Call this array v.
		3) v should satisfy the property that v[0,1,0,0,0,1,...,1,0], total of N entries, should give the entry of psi 
		   along the the spin-z basis vector direction (0,1,0,0,0,1,...,1,0). This ensures a correspondence of the v-indices
		   (and thus the psi-entries) to the N lattice sites.
		4) fix the lattice sites that define the subsystem N_A, and reshuffle the array v according to this: e.g. if the 
	 	   subsystem consistes of sites (k,l) then v should be reshuffled such that v[(k,l), (all other sites)]
	 	5) reshape v[(k,l), (all other sites)] into a 2D array of dimension ( N_A x N/N_A ) and proceed with the SVD as below  
		'''
		if chain_subsys==list(range(len(chain_subsys))):
			# chain_subsys sites come in consecutive order
			# define reshape tuple
			reshape_tuple2 = (Ns, Ns_A, basis.sps**N//Ns_A)
			# reshape states
			v = _np.reshape(psi.T, reshape_tuple2,order="F")
			del psi
		else: # if chain_subsys not consecutive or staring site not [0]
			# performs 2) and 3)
			# update reshape tuple
			reshape_tuple1 = (Ns,) + tuple([basis.sps for i in range(N)])
			# upadte axes dimensions
			system = [s+1 for s in system]
			system.insert(0,0)
			# reshape states
			v = _np.reshape(psi.T,reshape_tuple1,order="F")
			del psi
			# performs 4)
			v=v.transpose(system) 
			# performs 5)
			reshape_tuple2 = (Ns, Ns_A, basis.sps**N//Ns_A)
			v = _np.reshape(v,reshape_tuple2,order="F")
			

	elif basis.__class__.__name__[:-6] == 'photon':

		# set chain subsys if not defined; 
		if chain_subsys is None: 
			chain_subsys=list(range( int(N) ))
			warnings.warn("subsystem set to the entire chain.",stacklevel=4)


		#calculate H-space dimensions of the subsystem and the system
		N_A = len(chain_subsys)
		Ns_A = basis.sps**N_A

		# define lattice indices putting the subsystem to the left
		system = chain_subsys[:]
		[system.append(i) for i in range(N) if not i in chain_subsys]
		
		# re-write the state in the initial basis
		if basis.Nph is not None: # no total particle conservation
			Nph = basis.Nph
			if basis.Ns < photon_Hspace_dim(N,basis.Ntot,basis.Nph): #chain symmetries present
				if N_A!=N: # doesn't make use of chain symmetries
					psi = basis.get_vec(psi,sparse=False,full_part=True)
				else: # makes use of symmetries
					Ns_chain = basis.chain_Ns
			else:
				Ns_chain = basis.sps**N

		elif basis.Ntot is not None: # total particle-conservation
			Nph = basis.Ntot
			if basis.Ns < photon_Hspace_dim(N,basis.Ntot,basis.Nph): #chain symmetries present
				if N_A==N: # make use of symmetries
					psi = basis.get_vec(psi,sparse=False,full_part=False)
					Ns_chain = basis.chain_Ns
				else: # doesn't make use of symmetries
					psi = basis.get_vec(psi,sparse=False,full_part=True)
					Ns_chain = basis.sps**N
			else: # no chain symmetries present
				if N_A==N:
					psi = basis.get_vec(psi,sparse=False,full_part=False)
				else:
					psi = basis.get_vec(psi,sparse=False,full_part=True)
				Ns_chain = basis.chain_Ns

		if chain_subsys == list(range(len(chain_subsys))): 
			# chain_subsys sites come in consecutive order or staring site not [0]
			# define reshape tuple
			if N_A==N: # chain_subsys equals entire lattice
				reshape_tuple2 = (Ns, Ns_chain,Nph+1)
			else: #chain_subsys is smaller than entire lattice
				reshape_tuple2 = (Ns, Ns_A, basis.sps**(N-N_A)*(Nph+1) )
			v = _np.reshape(psi.T,reshape_tuple2,order="F")
			del psi
		else: # if chain_subsys not consecutive
			# performs 2) and 3)	
			reshape_tuple1 = (Ns,) + tuple([basis.sps for i in range(N)]) + (Nph+1,)
			# upadte axes dimensions
			system = [s+1 for s in system]
			system.insert(0,0)
			# reshape states
			v = _np.reshape(psi.T, reshape_tuple1,order="F")
			del psi
			# performs 4)
			system.append(len(system))
			v=v.transpose(system)
			# performs 5)
			reshape_tuple2 = (Ns, Ns_A, basis.sps**(N-N_A)*(Nph+1) )
			v = _np.reshape(v,reshape_tuple2,order="F")
				
	else:
		raise ValueError("'basis' class {} not supported!".format(basis.__class__.__name__))

	return v, rho_d, N_A

def _inf_time_obs(rho,istate,Obs=False,delta_t_Obs=False,delta_q_Obs=False,Sd_Renyi=False,Srdm_Renyi=False,alpha=1.0):
	"""
	This function calculates various quantities (observables, fluctuations, entropies) written in the
	diagonal basis of a density matrix 'rho'. See also documentation of 'Diagonal_Ensemble'. The 
	fuction is vectorised, meaning that 'rho' can be an array containing the diagonal density matrices
	in the columns.

	RETURNS:	dictionary with keys corresponding to the observables

	--- variables --- 

	istate: (required) type of initial state. Allowed strings are 'pure', 'DM', 'mixed', 'thermal'.

	Obs: (optional) array of shape (,1) with the diagonal matrix elements of an observable in the basis
			where the density matrix 'rho' is diagonal.

	delta_t_Obs: (optional) array of shape (1,1) containing the off-diagonal matrix elements of the 
			square of an observable, to evaluate the infinite-time temporal fluctuations

	delta_q_Obs: (optional) array containing the diagonal elements (Obs^2)_{nn} - (Obs_{nn})^2 in the 
			basis where the DM 'rho' is diagonal. Evaluates the infinite-time quantum fluctuations.

	Sd_Renyi: (optional) when set to 'True', returns the key with diagonal density matrix of 'rho'.

	Srdm_Renyi: (optional) (i,n) array containing the singular values of the i-th state of the eigenbasis
			of 'rho'. Returns the key with the entanglement _entropy of 'rho' reduced to a subsystem of
			given choice at infinite times.

	alpha: (optional) Renyi _entropy parameter. 
	""" 

	# if Obs or deltaObs: parse V2

	if isinstance(alpha,complex) or alpha < 0.0:
		raise TypeError("Renyi parameter 'alpha' must be real-valued and non-negative!")

	istates = ['pure', 'DM','mixed','thermal']
	if istate not in istates:
		raise TypeError("Uknown type 'istate' encountered! Try {}!".format(istates))

	# initiate observables dict
	variables = []


	if Obs is not False:
		variables.append("Obs_"+istate)
	if delta_t_Obs is not False:
		variables.append("delta_t_Obs_"+istate)
	if delta_q_Obs is not False:
		variables.append("delta_q_Obs_"+istate)
	if Sd_Renyi:
		if alpha == 1.0:
			variables.append("Sd_"+istate)
		else:
			variables.append("Sd_Renyi_"+istate)
	if Srdm_Renyi is not False:
		if alpha == 1.0:
			variables.append("Srdm_"+istate)
		else:
			variables.append("Srdm_Renyi_"+istate)


	#################################################################
	# calculate diag ens value of Obs
	if Obs is not False:
		Obs_d = Obs.dot(rho)


	# calculate diag ens value of Obs fluctuations
	if delta_t_Obs is not False:
		delta_t_Obs_d = _np.einsum('j...,jk,k...->...',rho,delta_t_Obs,rho).real

		# calculate diag ens value of Obs fluctuations
		if delta_q_Obs is not False:
			delta_q_Obs_d = _np.sqrt( _np.einsum('j...,j->...',rho,delta_q_Obs).real - delta_t_Obs_d - Obs_d**2 )

		delta_t_Obs_d = _np.sqrt( delta_t_Obs_d )

		
	# calculate Shannon _entropy for the distribution p
	def _entropy(p,alpha):
		""" 
		This function calculates the Renyi _entropy of the distribution p with parameter alpha.
		"""
		if alpha == 1.0:
			#warnings.warn("Renyi _entropy equals von Neumann _entropy.", UserWarning,stacklevel=4)
			S = - _np.nansum(p*_np.log(p),axis=0)
		else:
			S = 1.0/(1.0-alpha)*_np.log(_np.nansum(p**alpha,axis=0) )
			
		return S

	# calculate diag ens ent _entropy in post-quench basis
	if Srdm_Renyi is not False:
		# calculate effective diagonal singular values, \lambda_i^{(n)} = Srdm_Renyi
		#rho_ent = (Srdm_Renyi**2).dot(rho) # has components (i,psi)
		rho_ent = Srdm_Renyi # has components (i,psi)
		Srdm_Renyi_d = _entropy(rho_ent,alpha)

		
	# calculate diag ens _entropy in post-quench basis
	if Sd_Renyi:
		Sd_Renyi_d = _entropy(rho,alpha)
		

	# define return dict
	return_dict = {}
	for i in variables:

		j=i
		if alpha == 1.0 and ("Srdm" in i or 'Sd' in i):
			i=i.replace(istate,'Renyi_{}'.format(istate))

		return_dict[j] = locals()[i[:-len(istate)]+'d']
	

	return return_dict
		
def diag_ensemble(N,system_state,E2,V2,density=True,alpha=1.0,rho_d=False,Obs=False,delta_t_Obs=False,delta_q_Obs=False,Sd_Renyi=False,Srdm_Renyi=False,Srdm_args={}):
	"""
	This function calculates the expectation values of physical quantities in the Diagonal ensemble 
	set by the initial state (see eg. arXiv:1509.06411). Equivalently, these are the infinite-time 
	expectation values after a sudden quench at time t=0 from a Hamiltonian H1 to a Hamiltonian H2.


	RETURNS: 	dictionary with keys depending on the passed optional arguments:


	replace "..." below by 'pure', 'thermal' or 'mixed' depending on input params.

	'Obs_...': infinite time expectation of observable 'Obs'.

	'delta_t_Obs_...': infinite time temporal fluctuations of 'Obs'.

	'delta_q_Obs_...': infinite time quantum fluctuations of 'Obs'.

	'Sd_...' ('Sd_Renyi_...' for alpha!=1.0): Renyi _entropy of density matrix of Diagonal Ensemble with parameter 'alpha'.

	'Srdm_...' ('Srdm_Renyi_...' for alpha!=1.0): Renyi entanglement _entropy of reduced density matrix of Diagonal Ensemble 
			with parameter 'alpha'.

	'rho_d': density matrix of diagonal ensemble


	--- arguments ---


	N: (required) system size N.

	system_state: (required) the state of the quantum system. Can be a:

				-- pure state [numpy array of shape (Ns,) or (,Ns)].

				-- density matrix (DM) [numpy array of shape (Ns,Ns)].

				-- mixed DM [dictionary] {'V1':V1,'E1':E1,'f':f,'f_args':f_args,'V1_state':int,'f_norm':False} to 
					define a diagonal DM in the basis 'V1' of the Hamiltonian H1. The keys are

					All expectation values depend statistically on the symmetry block via the available number of 
					states as part of the system-size dependence!

					== 'V1': (required) array with the eigenbasis of H1 in the columns.

					== 'E1': (required) eigenenergies of H1.

					== 'f': (optional) the distribution used to define the mixed DM. Default is
						'f = lambda E,beta: numpy.exp(-beta*(E - E[0]) )'. 

					== 'f_args': (required) list of arguments of function 'f'. If 'f' is not defined, by 
						default we have 'f=numpy.exp(-beta*(E - E[0]))', and 'f_args' specifies the inverse temeprature list [beta].

					== 'V1_state' (optional) : list of integers to specify the states of 'V1' wholse pure 
						expectations are also returned.

					== 'f_norm': (optional) if set to 'False' the mixed DM built from 'f' is NOT normalised
						and the norm is returned under the key 'f_norm'. 

					The keys are CANNOT be chosen arbitrarily.

	V2: (required) numpy array containing the basis of the Hamiltonian H2 in the columns.

	E2: (required) numpy array containing the eigenenergies corresponding to the eigenstates in 'V2'.
		This variable is only used to check for degeneracies.

	rho_d: (optional) When set to 'True', returns the Diagonal ensemble DM under the key 'rho_d'. 

	Obs: (optional) hermitian matrix of the same size as V2, to calculate the Diagonal ensemble 
			expectation value of. Appears under the key 'Obs'.

	delta_t_Obs: (optional) TIME fluctuations around infinite-time expectation of 'Obs'. Requires 'Obs'. 
			Appears under the key 'delta_t_Obs'.

	delta_q_Obs: (optional) QUANTUM fluctuations of the expectation of 'Obs' at infinite-times. 
			Requires 'Obs'. Appears under the key 'delta_q_Obs'. Returns temporal fluctuations 
			'delta_t_Obs' for free.

	Sd_Renyi: (optional) diagonal Renyi _entropy in the basis of H2. The default Renyi parameter is 
			'alpha=1.0' (see below). Appears under the key Sd_Renyi'.

	Srdm_Renyi: (optional) entanglement Renyi _entropy of a subsystem of a choice. The default Renyi 
			parameter is 'alpha=1.0' (see below). Appears under the key Srdm_Renyi'. Requires 
			'Srdm_args'. To specify the subsystem, see documentation of '_reshape_as_subsys'.

	Srdm_args: (optional) dictionary of ent_entropy arguments, required when 'Srdm_Renyi = True'. The 
			following keys are allowed:

			* basis: (required) the basis used to build 'system_state'. Must be an instance of 'photon_basis',
			  'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'. 

			* chain_subsys: (optional) a list of lattice sites to specify the chain subsystem. Default is

			 * [0,1,...,N/2-1,N/2] for 'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'.

			 * [0,1,...,N-1,N] for 'photon_basis'. 

			 * subsys_ordering: (optional) if set to 'True', 'chain_subsys' is being ordered. Default is 'True'.

	density: (optional) if set to 'True', all observables are normalised by the system size N, except
				for the entanglement _entropy which is normalised by the subsystem size 
				[i.e., by the length of 'chain_subsys']. Detault is 'True'.

	alpha: (optional) Renyi alpha parameter. Default is '1.0'.
	"""

	# check if E2 are all unique
	E2 = _np.asarray(E2)
	if _np.any( _np.diff(_np.sort(E2)) < 1E3*_np.finfo(E2.dtype).eps):
		raise TypeError("Cannot use function 'diag_ensemble' with dengenerate e'values 'E2'!")
	del E2

	if N and not(type(N) is int):
		raise TypeError("System size 'N' must be a positive integer!")


	# various checks
	if delta_t_Obs or delta_q_Obs:
		if not Obs:
			raise TypeError("Expecting to parse the observable 'Obs' whenever 'delta_t_Obs = True' or 'delta_q_Obs = True'!")
	
	# calculate diagonal ensemble DM

	if isinstance(system_state,(list, tuple, _np.ndarray)): # initial state either pure or DM

		if len(system_state.shape)==1: # pure state
			istate = 'pure'
			# calculate diag ensemble DM
			rho = abs( system_state.conj().dot(V2) )**2;
		elif len(system_state.shape)==2: # DM
			istate = 'DM'
			# calculate diag ensemble DM
			rho = _np.einsum( 'ij,ji->i', V2.T.conj(), system_state.dot(V2) ).real

	
	elif isinstance(system_state,dict): # initial state is defined by diag distr
		# define allowed keys
		key_strings = ['V1','E1','f','f_args','V1_state','f_norm']

		if 'V1' in system_state.keys():
			V1 = system_state['V1']
		else:
			raise TypeError("Dictionary 'system_state' must contain states matrix 'V1'!")
		
		if 'E1' in system_state.keys():
			E1 = _np.asarray( system_state['E1'] )
			if any(sorted(E1)!=E1):
				raise TypeError("Expecting ordered vector of energies 'E1'!")
		else:
			raise TypeError("Dictionary 'system_state' must contain eigenvalues vector 'E1'!")
		
		if 'f_args' in system_state.keys():
			f_args = system_state['f_args']
		else:
			raise TypeError("Dictionary 'system_state' must contain function arguments list 'f_args'!")

		if 'V1_state' in system_state.keys():
			V1_state = system_state['V1_state']

		# check if user has passed the distribution 'f'
		if 'f' in system_state.keys():
			f = system_state['f']
			istate = 'mixed'
		else:
			istate = 'thermal'
			# define Gibbs distribution (up to normalisation)
			f = lambda E1,beta: _np.exp(-beta*(E1 - E1[0]))

		if 'f_norm' in system_state.keys():
			f_norm = system_state['f_norm']
			f_norms = _np.zeros((len(f_args[0])),dtype=type(f_args[0][0]) )
		else:
			f_norm = True

		if 'V1_state' in locals():
			if not all(isinstance(item, int) for item in V1_state):
				raise TypeError("Expecting an integer value for variable 'V1_state'!")
			if min(V1_state) < 0 or max(V1_state) > len(E1)-1:
				raise TypeError("Value 'V1_state' violates '0 <= V1_state <= len(E1)-1'!")

		# define diagonal (in V1) mixed DM
		
		rho_mixed = _np.zeros((len(E1),len(f_args[0])),dtype=type(f_args[0][0]) )
		for i, arg in enumerate(f_args[0]):
			if f_norm:
				rho_mixed[:,i] = f(E1,arg) / sum(f(E1,arg))
			else:
				rho_mixed[:,i] = f(E1,arg)
				# calculate normalisation
				f_norms[i] = sum(f(E1,arg))


		# calculate diag ensemble DM for each state in V1
		rho = abs( V2.conj().T.dot(V1) )**2 # components are (n,psi)

		del V1, E1
	else:
		raise TypeError("Wrong variable type for 'system_state'! E.g., use np.ndarray.")


	# clear up memory
	del system_state

	# add floating point number to zero elements
	rho[rho<=1E-16] = _np.finfo(rho.dtype).eps


	# prepare observables
	if Obs is not False or delta_t_Obs is not False or delta_q_Obs is not False:

		if (delta_t_Obs or delta_q_Obs) and Obs is not False:
			# diagonal matrix elements of Obs^2 in the basis V2
			#delta_t_Obs =  _np.einsum( 'ij,ji->i', V2.T.conj(), Obs.dot(Obs).dot(V2) ).real
			Obs = V2.T.conj().dot( Obs.dot(V2) )
			delta_t_Obs = _np.square(Obs)
			_np.fill_diagonal(delta_t_Obs,0.0)
			if delta_q_Obs is not False:
				delta_q_Obs = _np.diag(Obs.dot(Obs)).real
			Obs = _np.diag(Obs).real
			
		elif Obs is not False:
			# diagonal matrix elements of Obs in the basis V2
			Obs = _np.einsum('ij,ji->i', V2.transpose().conj(), Obs.dot(V2) ).real

		
	if Srdm_Renyi:
		"""
		# calculate singular values of columns of V2
		v, _, N_A = _reshape_as_subsys({"V_states":V2},**Srdm_args)

		U, lmbda, _ = _npla.svd(v, full_matrices=False)
		if istate in ['mixed','thermal']:
			DM_chain_subsys = _np.einsum('nm,nij,nj,nkj->mik',rho,U,lmbda**2,U.conj() )
		else:
			DM_chain_subsys = _np.einsum('n,nij,nj,nkj->ik',rho,U,lmbda**2,U.conj() )
			
		Srdm_Renyi = _npla.eigvalsh(DM_chain_subsys).T # components (i,psi)
		del v, U, DM_chain_subsys
		"""
		basis=Srdm_args['basis']
		partial_tr_args=Srdm_args.copy()
		del partial_tr_args['basis']
		if 'sub_sys_A' in Srdm_args:
			sub_sys_A = Srdm_args['sub_sys_A']
			del partial_tr_args['sub_sys_A']

		elif 'chain_subsys' in Srdm_args:
			sub_sys_A = Srdm_args['chain_subsys']
			del partial_tr_args['chain_subsys']
		else:
			sub_sys_A=tuple(range(basis.L//2))
		N_A=len(sub_sys_A)
		rdm_A = basis.partial_trace(V2,sub_sys_A=sub_sys_A,enforce_pure=True,**partial_tr_args)
		rdm = _np.einsum('n...,nij->...ij',rho,rdm_A)
	
		Srdm_Renyi = _npla.eigvalsh(rdm).T # components (i,psi) 
		
	# clear up memory
	del V2

	# calculate diag expectation values
	Expt_Diag = _inf_time_obs(rho,istate,alpha=alpha,Obs=Obs,delta_t_Obs=delta_t_Obs,delta_q_Obs=delta_q_Obs,Srdm_Renyi=Srdm_Renyi,Sd_Renyi=Sd_Renyi)
	

	Expt_Diag_Vstate={}
	# compute density
	for key,value in Expt_Diag.items():
		if density:
			if 'rdm' in key:
				value /= N_A
			else:
				value /= N

		Expt_Diag[key] = value
		# calculate thermal expectations
		if istate in ['mixed','thermal']:
			Expt_Diag_state = {}
			Expt_Diag[key] = value.dot(rho_mixed)
			# if 'GS' option is passed save GS value
			if 'V1_state' in locals():
				state_key = key[:-len(istate)]+'V1_state'
				Expt_Diag_Vstate[state_key] = value[V1_state]
			# merge state and mixed dicts
			Expt_Diag.update(Expt_Diag_state)

	if istate in ['mixed','thermal']:
		if f_norm==False:
			Expt_Diag['f_norm'] = f_norms
		if 'V1_state' in locals():
			Expt_Diag.update(Expt_Diag_Vstate)
			
	# return diag ensemble density matrix if requested
	if rho_d:
		if 'V1_state' in locals():
			Expt_Diag['rho_d'] = rho[:,V1_state]
		else:
			Expt_Diag['rho_d'] = rho


	return Expt_Diag

def ED_state_vs_time(psi,E,V,times,iterate=False):
	"""
	This routine calculates the time evolved initial state as a function of time. The initial 
	state is 'psi' and the time evolution is carried out under the Hamiltonian H with eigenenergies 
	'E' and eigensystem 'V'. 

	RETURNS:	either a matrix with the time evolved states as rows, 
				or an iterator which generates the states one by one.

	--- arguments --- 

	psi: (required) initial state.

	V: (required) unitary matrix containing in its columns all eigenstates of the Hamiltonian H. 

	E: (required) array containing the eigenvalues of the Hamiltonian H2. 
			The order of the eigenvalues must correspond to the order of the columns of V2. 

	times: (required) a vector of times to evaluate the time evolved state at. 

	iterate: (optional) if True this function returns the generator of the time evolved state. 
	"""
	psi = _np.squeeze(_np.asarray(psi))


	if V.ndim != 2 or V.shape[0] != V.shape[1]:
		raise ValueError("'V' must be a square matrix")

	if V.shape[0] != len(E):
		raise TypeError("Number of eigenstates in 'V' must equal number of eigenvalues in 'E'!")
	if psi.shape[0] != len(E):
		raise TypeError("Variables 'psi' and 'E' must have the same dimension!")

	if psi.ndim == 2:
		if psi.shape[0] != psi.shape[1]:
			raise ValueError("mixed states must be square!")

	if psi.ndim > 2:
		raise ValueError("psi must be 1 or 2 dimension array.")

	if _np.isscalar(times):
		TypeError("Variable 'times' must be a array or iter like object!")

	times = -1j*_np.asarray(times)
	

	# define generator of time-evolved state in basis V2
	def pure_t_iter(V,psi,times):
		# a_n: probability amplitudes
		# times: time vector
		a_n = V.T.conj().dot(psi)
		for t in times:
			yield V.dot( _np.exp(E*t)*a_n )

	def mixed_t_iter(V,psi,times):
		# a_n: probability amplitudes
		# times: time vector
		rho_d = V.T.conj().dot(psi.dot(V))
		for t in times:
			exp_t = _np.exp(t*E)
			yield _np.einsum("ij,j,jk,k,lk->il",V,exp_t,rho_d,exp_t.conj(),V.conj())


	if psi.ndim == 1:
		if iterate:
			return pure_t_iter(V,psi,times)
		else:
			c_n = V.T.conj().dot(psi)

			Ntime = len(times)
			Ns = len(E)

			psi_t = _np.broadcast_to(times,(Ns,Ntime)).T # generate [[-1j*times[0], ..., -1j*times[0]], ..., [-1j*times[-1], ..., -1j*times[01]]
			psi_t = psi_t*E # [[-1j*E[0]*times[0], ..., -1j*E[-1]*times[0]], ..., [-1j*E[0]*times[-1], ..., -1j*E[-1]*times[-1]]
			_np.exp(psi_t,psi_t) # [[exp(-1j*E[0]*times[0]), ..., exp(-1j*E[-1]*times[0])], ..., [exp(-1j*E[0]*times[-1]), ..., exp(-1j*E[01]*times[01])]

			psi_t *= c_n # [[c_n[0]exp(-1j*E[0]*times[0]), ..., c_n[-1]*exp(-1j*E[-1]*times[0])], ..., [c_n[0]*exp(-1j*E[0]*times[-1]), ...,c_n[o]*exp(-1j*E[01]*times[01])]

			# for each vector trasform back to original basis
			psi_t = V.dot(psi_t.T) 

			return psi_t # [ psi(times[0]), ...,psi(times[-1]) ]
	else:
		if iterate:
			return mixed_t_iter(V,psi,times)
		else:
			Ntime = len(times)
			Ns = len(E)

			rho_d = V.T.conj().dot(psi.dot(V))

			exp_t = _np.broadcast_to(times,(Ns,Ntime)).T # generate [[-1j*times[0], ..., -1j*times[0]], ..., [-1j*times[-1], ..., -1j*times[01]]
			exp_t = exp_t*E # [[-1j*E[0]*times[0], ..., -1j*E[-1]*times[0]], ..., [-1j*E[0]*times[-1], ..., -1j*E[-1]*times[-1]]
			_np.exp(exp_t,exp_t) # [[exp(-1j*E[0]*times[0]), ..., exp(-1j*E[-1]*times[0])], ..., [exp(-1j*E[0]*times[-1]), ..., exp(-1j*E[01]*times[01])]
			
			return _np.einsum("ij,tj,jk,tk,lk->ilt",V,exp_t,rho_d,exp_t.conj(),V.conj())

			

def obs_vs_time(psi_t,times,Obs_dict,enforce_pure=False,return_state=False,Sent_args={},disp=False):
	
	"""
	This routine calculates the expectation value of (a list of) observable(s) as a function of time 
	in the time-dependent state 'psi_t'.

	RETURNS:	dictionary with keys:

	'custom_name': for each key of 'Obs_dict', the time-dependent expectation of the 
				observable 'Obs_dict[key]' is calculated and returned.

	'psi_t': (optional) returns a 2D array the columns of which give the state at the associated time.

	'Sent_time': (optional) returns the entanglement _entropy of the state at time 'times'.

	--- arguments ---

	psi_t: (required) three different inputs:
		i) psi_t tuple(psi,E,V) 
			psi: initial state
	
			V: unitary matrix containing in its columns all eigenstates of the Hamiltonian H2. 

			E: real vector containing the eigenvalues of the Hamiltonian H2. 
			   The order of the eigenvalues must correspond to the order of the columns of V2.

		ii) numpy array or matrix with states in the columns.

		iii) generator which generates the states

	Obs_dict: (required) dictionary of hermitian matrices to calculate its time-dependent expectation value. 

	times: (required) a vector of times to evaluate the expectation value at. 

	return_state: (optional) when set to 'True' or Sent_args is nonempty, returns a matrix whose columns give the state vector 
			at the times specified by the column index. The return dictonary key is 'psi_time'.

	Srdm_args: (optional) dictionary of ent_entropy arguments, required when 'Srdm_Renyi = True'. The 
			following keys are allowed:

			* basis: (required) the basis used to build 'system_state'. Must be an instance of 'photon_basis',
			  'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'. 

			* chain_subsys: (optional) a list of lattice sites to specify the chain subsystem. Default is

			 * [0,1,...,N/2-1,N/2] for 'spin_basis_1d', 'fermion_basis_1d', 'boson_basis_1d'.

			 * [0,1,...,N-1,N] for 'photon_basis'. 

			 * subsys_ordering: (optional) if set to 'True', 'chain_subsys' is being ordered. Default is 'True'.

	"""

	
	variables = ['Expt_time']
	
	if not isinstance(Obs_dict,dict):
		raise ValueError("Obs_dict must be a dictionary.")

	num_Obs = len(Obs_dict.keys())

	for key, val in Obs_dict.items():
		if not _ishamiltonian(val):
			if not(_sp.issparse(val)) and not(val.__class__ in [_np.ndarray,_np.matrix]):
				val =_np.asanyarray(val)

			Obs_dict[key] = _hamiltonian([val],[],dtype=val.dtype)


	if type(psi_t) is tuple:

		psi,E,V = psi_t

		if V.ndim != 2 or V.shape[0] != V.shape[1]:
			raise ValueError("'V' must be a square matrix")
		if V.shape[0] != len(E):
			raise TypeError("Number of eigenstates in 'V' must equal number of eigenvalues in 'E'!")
		if len(psi) != len(E):
			raise TypeError("Variables 'psi' and 'E' must have the same dimension!")
		for Obs in Obs_dict.values():
			if V.shape != Obs._shape:
				raise TypeError("shapes of 'V1' and 'Obs' must be equal!")
			

		if _np.isscalar(times):
			TypeError("Variable 'times' must be a array or iter like object!")

		if return_state:
			variables.append("psi_t")

		
		# get iterator over time dependent state (see function above)
		if return_state:
			psi_t = ED_state_vs_time(psi,E,V,times,iterate=False)
		else:
			psi_t = ED_state_vs_time(psi,E,V,times,iterate=True)


	elif psi_t.__class__ in [_np.ndarray,_np.matrix]:


		for Obs in Obs_dict.values():
			if psi_t.shape[0] != Obs._shape[1]:
				raise ValueError("states must be in columns of input matrix.")


		if return_state:
			variables.append("psi_t")
		else:
			return_state=True # set to True to use einsum but do not return state

	elif _isgenerator(psi_t):
		if return_state:
			variables.append("psi_t")
			psi_t_list = []
			for psi in psi_t:
				psi_t_list.append(psi)

			psi_t = _np.squeeze(_np.dstack(psi_t_list))

			for Obs in Obs_dict.values():
				if psi_t.shape[0] != Obs._shape[1]:
					raise ValueError("states must be in columns of input matrix.")

	else:
		raise ValueError("input not recognized")
	
	# calculate observables and Sent
	Expt_time = {}
	calc_Sent = False
	
	if len(Sent_args) > 0:
		Sent_args = dict(Sent_args)
		basis = Sent_args.get("basis")
		if basis is None:
			raise ValueError("Sent_args requires 'basis' for calculation")
		if not isbasis(basis):
			raise ValueError("'basis' object must be a proper basis object")

		if "chain_subsys" in Sent_args or"DM" in Sent_args or "svd_return_vec" in Sent_args:
			calc_ent_entropy = ent_entropy
		else:
			calc_ent_entropy = basis.ent_entropy
			del Sent_args["basis"]

		calc_Sent = True
		variables.append("Sent_time")
	
	if return_state:
		for key,Obs in Obs_dict.items():
			Expt_time[key]=Obs.expt_value(psi_t,time=times,check=False,enforce_pure=enforce_pure).real
			
		# calculate entanglement _entropy if requested	
		if calc_Sent:
			Sent_time = calc_ent_entropy(psi_t,**Sent_args)


	else:
		psi = next(psi_t) # get first state from iterator.
		# do first calculations of loop

		time = times[0]

		for key,Obs in Obs_dict.items():
			
			val = Obs.expt_value(psi,time=time,check=False).real
			dtype = _np.dtype(val)
			Expt_time[key] = _np.zeros((len(times),),dtype=dtype)
			Expt_time[key][0] = val



		# get initial dictionary from ent_entropy function
		# use this to set up dictionary for the rest of calculation.
		if calc_Sent:
			Sent_time = calc_ent_entropy(psi,**Sent_args)

			for key,val in Sent_time.items():
				val = _np.asarray(val)
				dtype = val.dtype
				shape = (len(times),) + val.shape
				Sent_time[key] = _np.zeros(shape,dtype=dtype)
				Sent_time[key][0] = val

		# loop over psi generator
		for m,psi in enumerate(psi_t):

			time = times[m+1]

			if disp: print("obs_vs_time integrated to t={:.4f}".format(time))

			for key,Obs in Obs_dict.items():
				Expt_time[key][m+1] = Obs.expt_value(psi,time=time,check=False).real

			if calc_Sent:
				Sent_time_update = calc_ent_entropy(psi,**Sent_args)
				for key in Sent_time.keys():
					Sent_time[key][m+1] = Sent_time_update[key]

		
	return_dict = {}
	for i in variables:
		if i == 'Expt_time':
			for key,val in Expt_time.items():
				return_dict[key] = _np.asarray(val)
		else:
			return_dict[i] = locals()[i]

	return return_dict

def project_op(Obs,proj,dtype=_np.complex128):
	"""
	This function takes an observable 'Obs' and a reduced basis or a projector and projects 'Obs'
	onto that reduced basis.

	RETURNS: 	dictionary with keys 

	'Proj_Obs': projected observable 'Obs'

	--- arguments ---

	Obs: (required) operator to be projected.

	proj: (required) basis of the final space after the projection or a matrix which contains the projector.

	dtype: (optional) data type. Default is np.complex128.

	"""

	variables = ["Proj_Obs"]

	if isbasis(proj):
		proj = proj.get_proj(dtype)
	elif (proj.__class__ not in [_np.ndarray,_np.matrix]) and (not _sp.issparse(proj)):
		raise ValueError("Expecting either matrix/array or basis object for proj argument.")

	if _ishamiltonian(Obs):

		if Obs.Ns != proj.shape[0]:
			if Obs.Ns != proj.shape[1]:
				raise ValueError("Dimension mismatch Obs:{0} proj{1}".format(Obs.get_shape,proj.shape))
			else:
				# projecting from a smaller to larger H-space
				proj_down=False
		else:
			# projecting from larger to smaller H-space
			proj_down=True

		if proj_down:
			Proj_Obs = Obs.project_to(proj)		
		else:
			Proj_Obs = Obs.project_to(proj.T.conj())

	else:

		if Obs.ndim != 2:
			raise ValueError("Expecting Obs to be a 2 dimensional array.")

		if Obs.shape[0] != Obs.shape[1]:
			raise ValueError("Expecting Obs to be a square array.")

		if Obs.shape[1] != proj.shape[0]:
			if Obs.shape[0] != proj.shape[1]:
				raise ValueError("Dimension mismatch Obs:{0} proj{1}".format(Obs.shape,proj.shape))
			else:
				proj_down=False
		else:
			proj_down=True

		if proj_down:
			Proj_Obs = proj.T.conj().dot(Obs.dot(proj))
		else:
			Proj_Obs = proj.dot(Obs.dot(proj.T.conj()))

	# define dictionary with outputs
	return_dict = {}
	for i in range(len(variables)):
		return_dict[variables[i]] = locals()[variables[i]]

	return return_dict

def KL_div(p1,p2):
	"""
	This routine returns the Kullback-Leibler divergence of the discrete probability distributions 
	p1 and p2.
	"""
	p1 = _np.asarray(p1)
	p2 = _np.asarray(p2)


	if len(p1) != len(p2):
		raise TypeError("Expecting the probability distributions 'p1' and 'p2' to have same size!")
	if p1.ndim != 1 or p2.ndim != 1:
		raise TypeError("Expecting the probability distributions 'p1' and 'p2' to have linear dimension!")


	if _np.any(p1<=0.0) or _np.any(p2<=0.0):
		raise TypeError("Expecting all entries of the probability distributions 'p1' and 'p2' to be non-negative!")
	
	if abs(sum(p1)-1.0) > 1E-13:
		raise ValueError("Expecting 'p1' to be normalised!")

	if abs(sum(p2)-1.0) > 1E-13:
		raise ValueError("Expecting 'p2' to be normalised!")

	if _np.any(p1==0.0):

		inds = _np.where(p1 == 0)

		p1 = _np.delete(p1,inds)
		p2 = _np.delete(p2,inds)

	return _np.multiply( p1, _np.log( _np.divide(p1,p2) ) ).sum()

def mean_level_spacing(E):
	"""
	This routine calculates the mean-level spacing 'r_ave' of the energy distribution E, see arXiv:1212.5611.

	RETURNS: float with mean-level spacing 'r_ave'.

	--- arguments ---

	E: (required) ordered list of ascending, nondegenerate eigenenergies.
	"""

	if not isinstance(E,_np.ndarray):
		E = _np.asarray(E)

	if _np.any(_np.sort(E)!=E):
		raise TypeError("Expecting a sorted list of ascending, nondegenerate eigenenergies 'E'.")

	# compute consecutive E-differences
	sn = _np.diff(E)
	# check for degeneracies
	if len(_np.unique(E)) != len(E):
		raise ValueError("Degeneracies found in spectrum 'E'!")
	# calculate the ratios of consecutive spacings
	aux = _np.zeros((len(E)-1,2),dtype=_np.float64)

	aux[:,0] = sn
	aux[:,1] = _np.roll(sn,-1)

	return _np.mean(_np.divide( aux.min(1), aux.max(1) )[0:-1] )



def evolve(v0,t0,times,f,solver_name="dop853",real=False,stack_state=False,verbose=False,imag_time=False,iterate=False,f_params=(),**solver_args):
	"""
	This function implements (imaginary) time evolution for a user-defined first-order f function.

	RETURNS: 	array containing evolved state in time

	--- arguments ---

	* `v0`: (required) initial state

	* `t0`: (required) initial time

	* `times`: (required) vector of times to evaluate the time-evolved state at

	* `f`: (required) user-defined `f` function (all derivatives must be first order)

	* `solver_name`: (optional) scipy solver integrator. Default is `dop853`.

	* `real`: (optional) flag to determine if `f` is real or complex-valued. Default is `False`.

	* `stack_state`: (optional) if `f` is written to take care of real and imaginary parts separately, this flag will take this into account. Default is `False`.

	* `verbose`: (optional) prints normalisation of state at teach time in `times`

	* `imag_time`: (optional) must be set to `True` when `f` defines imaginary-time evolution, in order to normalise the state at each time in `times`. Default is `False`.

	* `iterate`: (optional) creates a generator object to time-evolve the state. Default is `False`.

	* `f_params`: (optional) a tuple to pass all parameters of the function `f` to solver. Default is `f_params=()`.

	* `solver_args`: (optional) dictionary with additional [scipy integrator (solver)](https://docs.scipy.org/doc/scipy/reference/tutorial/integrate.html) arguments.	
		"""

	from scipy.integrate import complex_ode
	from scipy.integrate import ode

	if v0.ndim > 2:
		raise ValueError("state mush have ndim < 3.")

	shape0 = v0.shape

	if v0.ndim == 2:
		if v0.shape[0] != v0.shape[1]:
			v0 = v0.ravel()
	 
	
	if _np.iscomplexobj(times):
		raise ValueError("times must be real number(s).")

	#v0 = v0.ravel()
	n = _np.linalg.norm(v0) # needed for imaginary time to preserve the proper norm of the state. 



	if stack_state:
		v1 = v0
		v0 = _np.zeros(2*shape0[0],dtype=v1.real.dtype)
		v0[:shape0[0]] = v1.real
		v0[shape0[0]:] = v1.imag
		solver = ode(f) # y_f = f(t,y,*args)
	elif real:
		solver = ode(f) # y_f = f(t,y,*args)
	else:
		solver = complex_ode(f) # y_f = f(t,y,*args)

	

	if solver_name in ["dop853","dopri5"]:
		if solver_args.get("nsteps") is None:
			solver_args["nsteps"] = _np.iinfo(_np.int32).max
		if solver_args.get("rtol") is None:
			solver_args["rtol"] = 1E-9
		if solver_args.get("atol") is None:
			solver_args["atol"] = 1E-9


				

	solver.set_integrator(solver_name,**solver_args)
	solver.set_f_params(*f_params)
	solver.set_initial_value(v0, t0)

	if _np.isscalar(times):
		return _evolve_scalar(solver,v0,t0,times,stack_state,imag_time,n,shape0)
	else:
		if iterate:
			return _evolve_iter(solver,v0,t0,times,verbose,stack_state,imag_time,n,shape0)
		else:
			return _evolve_list(solver,v0,t0,times,verbose,stack_state,imag_time,n,shape0)


def _evolve_scalar(solver,v0,t0,time,stack_state,imag_time,n,shape0):
	from numpy.linalg import norm
	Ns=shape0[0]

	if time == t0:
		if stack_state:
			return (v0[:Ns] + 1j*v0[Ns:]).reshape(shape0)
		else:
			return _np.array(v0).reshape(shape0)

	solver.integrate(time)
	if solver.successful():
		if imag_time: solver._y /= (norm(solver._y)/n)
		if stack_state:
			return (solver.y[:Ns] + 1j*solver.y[Ns:]).reshape(shape0)
		else:
			return _np.array(solver.y).reshape(shape0)
	else:
		raise RuntimeError("failed to evolve to time {0}, nsteps might be too small".format(time))	



def _evolve_list(solver,v0,t0,times,verbose,stack_state,imag_time,n,shape0):
	from numpy.linalg import norm

	Ns=shape0[0]
	v = _np.empty(shape0+(len(times),),dtype=_np.complex128)
	
	for i,t in enumerate(times):

		if t == t0:
			if verbose: print("evolved to time {0}, norm of state {1}".format(t,_np.linalg.norm(solver.y)))
			if stack_state:
				v[...,i] = (v0[:Ns] + 1j*v0[Ns:]).reshape(shape0)
			else:
				v[...,i] = _np.array(v0).reshape(shape0)
			continue

		solver.integrate(t)
		if solver.successful():
			if verbose: print("evolved to time {0}, norm of state {1}".format(t,_np.linalg.norm(solver.y)))
			if imag_time: solver._y /= (norm(solver._y)/n)
			if stack_state:
				v[...,i] = (solver.y[:Ns] + 1j*solver.y[Ns:]).reshape(shape0)
			else:
				v[...,i] = solver.y.reshape(shape0)
		else:
			raise RuntimeError("failed to evolve to time {0}, nsteps might be too small".format(t))
			

	return v



def _evolve_iter(solver,v0,t0,times,verbose,stack_state,imag_time,n,shape0):
	from numpy.linalg import norm
	Ns=shape0[0]


	for i,t in enumerate(times):
		if t == t0:
			if verbose: print("evolved to time {0}, norm of state {1}".format(t,_np.linalg.norm(solver.y)))
			if stack_state:
				yield (v0[:Ns] + 1j*v0[Ns:]).reshape(shape0)
			else:
				yield _np.array(v0).reshape(shape0)
			continue
			

		solver.integrate(t)
		if solver.successful():
			if verbose: print("evolved to time {0}, norm of state {1}".format(t,_np.linalg.norm(solver.y)))
			if imag_time: solver._y /= (norm(solver._y)/n)
			if stack_state:
				yield (solver.y[:Ns] + 1j*solver.y[Ns:]).reshape(shape0)
			else:
				yield solver.y.reshape(shape0)
		else:
			raise RuntimeError("failed to evolve to time {0}, nsteps might be too small".format(t))


