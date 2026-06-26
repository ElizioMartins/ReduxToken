use pyo3::prelude::*;

mod compressor;
mod filters;
mod stats;

use compressor::Compressor;
use stats::CompressionStats;

#[pyclass]
struct PyCompressor {
    inner: Compressor,
}

#[pymethods]
impl PyCompressor {
    #[new]
    fn new() -> Self {
        Self { inner: Compressor::default() }
    }

    fn compress(&self, py: Python<'_>, text: &str) -> PyResult<(String, Py<CompressionStats>)> {
        let (result, stats) = self.inner.compress(text);
        Ok((result, Py::new(py, stats)?))
    }
}

#[pymodule]
fn redux_token_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCompressor>()?;
    m.add_class::<CompressionStats>()?;
    Ok(())
}
