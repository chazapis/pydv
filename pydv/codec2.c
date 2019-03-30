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
#include <codec2/golay23.h>

void py_codec2_destroy(PyObject *capsule) {
    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return;

    // printf("Destroying state %p\n", state);
    codec2_destroy(state);
}

static PyObject* py_codec2_create(PyObject* self, PyObject *args) {
    int mode;

    if (!PyArg_ParseTuple(args, "i", &mode))
        return NULL;

    struct CODEC2 *state = codec2_create(mode);
    if (state == NULL)
        return NULL;

    // printf("Created state %p\n", state);
    return PyCapsule_New((void *)state, NULL, py_codec2_destroy);
}

static PyObject *py_codec2_encode(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    const char *buffer;
    Py_ssize_t count;

    if (!PyArg_ParseTuple(args, "Os#", &capsule, &buffer, &count))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    int nsam = codec2_samples_per_frame(state);

    if ((count / sizeof(short)) != nsam) {
        fprintf(stderr, "pydv.codec2.codec2_encode: input should be %d samples\n", nsam);
        return NULL;
    }

    int nbit = codec2_bits_per_frame(state);
    int nbyte = (nbit + 7) / 8;
    unsigned char *bits = (unsigned char *)malloc(nbyte);

    codec2_encode(state, bits, (short *)buffer);

    PyObject *item = Py_BuildValue("s#", bits, nbyte);
    free(bits);
    return item;
}

static PyObject *py_codec2_decode(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    const char *buffer;
    Py_ssize_t count;

    if (!PyArg_ParseTuple(args, "Os#", &capsule, &buffer, &count))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    int nbit = codec2_bits_per_frame(state);
    int nbyte = (nbit + 7) / 8;

    if (count != nbyte) {
        fprintf(stderr, "pydv.codec2.codec2_decode: input should be %d bytes\n", nbyte);
        return NULL;
    }

    int nsam = codec2_samples_per_frame(state);
    short *sound = (short *)malloc(nsam * sizeof(short));

    codec2_decode(state, sound, (unsigned char *)buffer);

    PyObject *item = Py_BuildValue("s#", sound, nsam * sizeof(short));
    free(sound);
    return item;
}

static PyObject *py_codec2_decode_ber(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    const char *buffer;
    Py_ssize_t count;
    float ber;

    if (!PyArg_ParseTuple(args, "Os#f", &capsule, &buffer, &count, &ber))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    int nbit = codec2_bits_per_frame(state);
    int nbyte = (nbit + 7) / 8;

    if (count != nbyte) {
        fprintf(stderr, "pydv.codec2.codec2_decode_ber: input should be %d bytes\n", nbyte);
        return NULL;
    }

    int nsam = codec2_samples_per_frame(state);
    short *sound = (short *)malloc(nsam * sizeof(short));

    codec2_decode_ber(state, sound, (unsigned char *)buffer, ber);

    PyObject *item = Py_BuildValue("s#", sound, nsam * sizeof(short));
    free(sound);
    return item;
}

static PyObject *py_codec2_samples_per_frame(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Getting samples per frame of state %p\n", state);
    return Py_BuildValue("i", codec2_samples_per_frame(state));
}

static PyObject *py_codec2_bits_per_frame(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Getting bits per frame of state %p\n", state);
    return Py_BuildValue("i", codec2_bits_per_frame(state));
}

static PyObject *py_codec2_set_lpc_post_filter(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    int enable, bass_boost;
    float beta, gamma;

    if (!PyArg_ParseTuple(args, "Oiiff", &capsule, &enable, &bass_boost, &beta, &gamma))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Setting lpc post filter of state %p to %d %d %f %f\n", state, enable, bass_boost, beta, gamma);
    codec2_set_lpc_post_filter(state, enable, bass_boost, beta, gamma);
    Py_RETURN_NONE;
}

static PyObject *py_codec2_get_spare_bit_index(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;

    if (!PyArg_ParseTuple(args, "O", &capsule))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Getting spare bit index of state %p\n", state);
    return Py_BuildValue("i", codec2_get_spare_bit_index(state));
}

static PyObject *py_codec2_set_natural_or_gray(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    int gray;

    if (!PyArg_ParseTuple(args, "Oi", &capsule, &gray))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    // printf("Setting natural or gray of state %p to %d\n", state, gray);
    codec2_set_natural_or_gray(state, gray);
    Py_RETURN_NONE;
}

static PyObject *py_codec2_get_energy(PyObject *self, PyObject *args) {
    PyObject *capsule = NULL;
    const char *buffer;
    Py_ssize_t count;

    if (!PyArg_ParseTuple(args, "Os#", &capsule, &buffer, &count))
        return NULL;

    struct CODEC2 *state = (struct CODEC2 *)PyCapsule_GetPointer(capsule, NULL);
    if (state == NULL)
        return NULL;

    int nbit = codec2_bits_per_frame(state);
    int nbyte = (nbit + 7) / 8;

    if (count != nbyte) {
        fprintf(stderr, "pydv.codec2.codec2_get_energy: input should be %d bytes\n", nbyte);
        return NULL;
    }

    return Py_BuildValue("f", codec2_get_energy(state, (unsigned char *)buffer));
}

static PyObject* py_golay23_init(PyObject* self) {
    golay23_init();
    Py_RETURN_NONE;
}

static PyObject *py_golay23_encode(PyObject *self, PyObject *args) {
    int data;

    if (!PyArg_ParseTuple(args, "i", &data))
        return NULL;

    return Py_BuildValue("i", golay23_encode(data));
}

static PyObject *py_golay23_decode(PyObject *self, PyObject *args) {
    int received_codeword;

    if (!PyArg_ParseTuple(args, "i", &received_codeword))
        return NULL;

    return Py_BuildValue("i", golay23_decode(received_codeword));
}

static PyObject *py_golay23_count_errors(PyObject *self, PyObject *args) {
    int received_codeword, corrected_codeword;

    if (!PyArg_ParseTuple(args, "ii", &received_codeword, &corrected_codeword))
        return NULL;

    return Py_BuildValue("i", golay23_count_errors(received_codeword, corrected_codeword));
}

static PyMethodDef codec2_funcs[] = {
    // codec2.h functions
    {"codec2_create", py_codec2_create, METH_VARARGS, NULL},
    {"codec2_encode", py_codec2_encode, METH_VARARGS, NULL},
    {"codec2_decode", py_codec2_decode, METH_VARARGS, NULL},
    {"codec2_decode_ber", py_codec2_decode_ber, METH_VARARGS, NULL},
    {"codec2_samples_per_frame", py_codec2_samples_per_frame, METH_VARARGS, NULL},
    {"codec2_bits_per_frame", py_codec2_bits_per_frame, METH_VARARGS, NULL},
    {"codec2_set_lpc_post_filter", py_codec2_set_lpc_post_filter, METH_VARARGS, NULL},
    {"codec2_get_spare_bit_index", py_codec2_get_spare_bit_index, METH_VARARGS, NULL},
    // {"codec2_rebuild_spare_bit", py_codec2_rebuild_spare_bit, METH_VARARGS, NULL},
    {"codec2_set_natural_or_gray", py_codec2_set_natural_or_gray, METH_VARARGS, NULL},
    // {"codec2_set_softdec", py_codec2_set_softdec, METH_VARARGS, NULL},
    {"codec2_get_energy", py_codec2_get_energy, METH_VARARGS, NULL},

    // golay23.h functions
    {"golay23_init", (PyCFunction)py_golay23_init, METH_NOARGS, NULL},
    {"golay23_encode", py_golay23_encode, METH_VARARGS, NULL},
    {"golay23_decode", py_golay23_decode, METH_VARARGS, NULL},
    {"golay23_count_errors", py_golay23_count_errors, METH_VARARGS, NULL},
    // {"golay23_syndrome", py_golay23_syndrome, METH_VARARGS, NULL},

    {NULL}
};

void initcodec2(void) {
    PyObject *module;

    module = Py_InitModule3("codec2", codec2_funcs, "Python interface to codec2");

    PyModule_AddIntConstant(module, "CODEC2_VERSION_MAJOR", CODEC2_VERSION_MAJOR);
    PyModule_AddIntConstant(module, "CODEC2_VERSION_MINOR", CODEC2_VERSION_MINOR);
    PyModule_AddStringConstant(module, "CODEC2_VERSION", CODEC2_VERSION);

    PyModule_AddIntConstant(module, "CODEC2_MODE_3200", 0);
    PyModule_AddIntConstant(module, "CODEC2_MODE_2400", 1);
    PyModule_AddIntConstant(module, "CODEC2_MODE_1600", 2);
    PyModule_AddIntConstant(module, "CODEC2_MODE_1400", 3);
    PyModule_AddIntConstant(module, "CODEC2_MODE_1300", 4);
    PyModule_AddIntConstant(module, "CODEC2_MODE_1200", 5);
    PyModule_AddIntConstant(module, "CODEC2_MODE_700", 6);
    PyModule_AddIntConstant(module, "CODEC2_MODE_700B", 7);
    PyModule_AddIntConstant(module, "CODEC2_MODE_700C", 8);
    PyModule_AddIntConstant(module, "CODEC2_MODE_450", 9);
    PyModule_AddIntConstant(module, "CODEC2_MODE_450PWB", 10);
    PyModule_AddIntConstant(module, "CODEC2_MODE_WB", 11);
}
