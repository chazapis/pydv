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
#include <codec2/codec2.h>

void free_state(PyObject *capsule) {
    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return;

    printf("Destroying state %p\n", state);
    codec2_destroy(state);
}

static PyObject* init_state(PyObject* self, PyObject *args) {
    int mode;

    if (!PyArg_ParseTuple(args, "i", &mode))
        return NULL;

    struct CODEC2 *state = codec2_create(mode);
    if (state == NULL)
        return NULL;

    printf("Created state %p\n", state);
    return PyCapsule_New((void *)state, NULL, free_state);
}

static PyObject *samples_per_frame(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    printf("Getting samples per frame of state %p\n", state);
    return Py_BuildValue("i", codec2_samples_per_frame(state));
}

static PyObject *bits_per_frame(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    printf("Getting bits per frame of state %p\n", state);
    return Py_BuildValue("i", codec2_bits_per_frame(state));
}

static PyObject *get_spare_bit_index(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    printf("Getting spare bit index of state %p\n", state);
    return Py_BuildValue("i", codec2_get_spare_bit_index(state));
}

static PyMethodDef codec2_funcs[] = {
    {"init_state", init_state, METH_VARARGS, NULL},
    // {"encode", encode, METH_VARARGS, NULL},
    // {"decode", decode, METH_VARARGS, NULL},
    // {"decode_ber", decode_ber, METH_VARARGS, NULL},
    {"samples_per_frame", samples_per_frame, METH_VARARGS, NULL},
    {"bits_per_frame", bits_per_frame, METH_VARARGS, NULL},
    // {"set_lpc_post_filter", set_lpc_post_filter, METH_VARARGS, NULL},
    {"get_spare_bit_index", get_spare_bit_index, METH_VARARGS, NULL},
    // {"rebuild_spare_bit", rebuild_spare_bit, METH_VARARGS, NULL},
    // {"set_natural_or_gray", set_natural_or_gray, METH_VARARGS, NULL},
    // {"set_softdec", set_softdec, METH_VARARGS, NULL},
    // {"get_energy", get_energy, METH_VARARGS, NULL},
    {NULL}
};

void initcodec2(void) {
    PyObject *module;

    module = Py_InitModule3("codec2", codec2_funcs, "Python interface to codec2");

    PyModule_AddIntConstant(module, "VERSION_MAJOR", CODEC2_VERSION_MAJOR);
    PyModule_AddIntConstant(module, "VERSION_MINOR", CODEC2_VERSION_MINOR);
    PyModule_AddStringConstant(module, "VERSION", CODEC2_VERSION);

    PyModule_AddIntConstant(module, "MODE_3200", 0);
    PyModule_AddIntConstant(module, "MODE_2400", 1);
    PyModule_AddIntConstant(module, "MODE_1600", 2);
    PyModule_AddIntConstant(module, "MODE_1400", 3);
    PyModule_AddIntConstant(module, "MODE_1300", 4);
    PyModule_AddIntConstant(module, "MODE_1200", 5);
    PyModule_AddIntConstant(module, "MODE_700", 6);
    PyModule_AddIntConstant(module, "MODE_700B", 7);
    PyModule_AddIntConstant(module, "MODE_700C", 8);
    PyModule_AddIntConstant(module, "MODE_450", 9);
    PyModule_AddIntConstant(module, "MODE_450PWB", 10);
    PyModule_AddIntConstant(module, "MODE_WB", 11);
}
