// Copyright (C) 2018 Antony Chazapis SV9OAN
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include <mbelib.h>

const int dW[72] = {
    0, 0, 3, 2, 1, 1, 0, 0, 1, 1, 0, 0, // 0-11
    3, 2, 1, 1, 3, 2, 1, 1, 0, 0, 3, 2, // 12-23
    0, 0, 3, 2, 1, 1, 0, 0, 1, 1, 0, 0, // 24-35
    3, 2, 1, 1, 3, 2, 1, 1, 0, 0, 3, 2, // 36-47
    0, 0, 3, 2, 1, 1, 0, 0, 1, 1, 0, 0, // 48-59
    3, 2, 1, 1, 3, 3, 2, 1, 0, 0, 3, 3  // 60-71
};

const int dX[72] = {
    10, 22, 11,  9, 10, 22, 11, 23,  8, 20,  9, 21, // 0-11
    10,  8,  9, 21,  8,  6,  7, 19,  8, 20,  9,  7, // 12-23
     6, 18,  7,  5,  6, 18,  7, 19,  4, 16,  5, 17, // 24-35
     6,  4,  5, 17,  4,  2,  3, 15,  4, 16,  5,  3, // 36-47
     2, 14,  3,  1,  2, 14,  3, 15,  0, 12,  1, 13, // 48-59
     2,  0,  1, 13,  0, 12, 10, 11,  0, 12,  1, 13  // 60-71
};

struct mbelib_state {
    mbe_parms cur_mp;
    mbe_parms prev_mp;
    mbe_parms prev_mp_enhanced;

    short aout_buf[160];

    int errs;
    int errs2;
    char err_str[64];

    int uvquality;
};

void free_state(PyObject *capsule) {
    struct mbelib_state *state = (struct mbelib_state *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return;

    // printf("Freeing state %p\n", state);
    free(state);
}

static PyObject* init_state(PyObject* self) {
    struct mbelib_state *state = (struct mbelib_state *)malloc(sizeof(struct mbelib_state));
    if (state == NULL)
        return NULL;

    mbe_initMbeParms(&state->cur_mp, &state->prev_mp, &state->prev_mp_enhanced);
    state->errs = 0;
    state->errs2 = 0;
    state->err_str[0] = 0;
    state->uvquality = 3;

    // printf("Allocated state %p\n", state);
    return PyCapsule_New((void *)state, NULL, free_state);
}

static PyObject *set_uvquality(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    int uvquality;
    if (!PyArg_ParseTuple(args, "Oi", &capsule, &uvquality))
        return NULL;

    struct mbelib_state *state = (struct mbelib_state *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Setting uvquality in state %p to value %d\n", state, uvquality);
    state->uvquality = uvquality;

    Py_RETURN_NONE;
}

static PyObject *get_uvquality(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct mbelib_state *state = (struct mbelib_state *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Getting uvquality of state %p\n", state);
    return Py_BuildValue("i", state->uvquality);
}

static PyObject *decode_dstar(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    const char *buffer;
    Py_ssize_t count;

    if (!PyArg_ParseTuple(args, "Os#", &capsule, &buffer, &count))
        return NULL;
    if (count != 9) {
        fprintf(stderr, "pydv.mbelib.decode_dstar: input should be 9 bytes\n");
        return NULL;
    }

    struct mbelib_state *state = (struct mbelib_state *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    char ambe_fr[4][24];
    char ambe_d[49];
    int i, dibit;
    const int *w, *x;

    memset(ambe_fr, 0, 4 * 24);
    memset(ambe_d, 0, 49);
    w = dW;
    x = dX;
    for (i = 0; i < 72; i++) {
        dibit = (buffer[i / 8] >> (i % 8)) & 1;
        ambe_fr[*w][*x] = dibit;
        w++;
        x++;
    }

    // printf("Decoding AMBE with state %p\n", state);
    mbe_processAmbe3600x2400Frame(state->aout_buf, &state->errs, &state->errs2, state->err_str, ambe_fr, ambe_d, &state->cur_mp, &state->prev_mp, &state->prev_mp_enhanced, state->uvquality);

    PyObject *result = PyTuple_New(160);
    if (result == NULL)
        return NULL;

    PyObject *item;
    for (i = 0; i < 160; i++) {
        item = Py_BuildValue("i", state->aout_buf[i]);
        if (item == NULL) {
            return NULL;
        }
        PyTuple_SetItem(result, i, item);
    }

    return result;
}

static PyMethodDef mbelib_funcs[] = {
    {"init_state", (PyCFunction)init_state, METH_NOARGS, NULL},
    {"set_uvquality", set_uvquality, METH_VARARGS, NULL},
    {"get_uvquality", get_uvquality, METH_VARARGS, NULL},
    {"decode_dstar", decode_dstar, METH_VARARGS, NULL},
    {NULL}
};

void initmbelib(void) {
    Py_InitModule3("mbelib", mbelib_funcs, "Python interface to mbelib");
}
