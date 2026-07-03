use pyo3::prelude::*;

pub mod compressor;
pub mod filters;
pub mod rev;
pub mod stats;

pub use compressor::Compressor;
pub use stats::CompressionStats;

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

    /// Compressão reversível: devolve (texto, stats, [(ref, original), ...]).
    fn compress_reversible(
        &self,
        py: Python<'_>,
        text: &str,
    ) -> PyResult<(String, Py<CompressionStats>, Vec<(String, String)>)> {
        let (result, stats, spans) = self.inner.compress_rev(text);
        Ok((result, Py::new(py, stats)?, spans))
    }
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCompressor>()?;
    m.add_class::<CompressionStats>()?;
    Ok(())
}
