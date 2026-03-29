#pragma once

#ifndef TENSOR_GPU_H
#define TENSOR_GPU_H

#include <vector>
#include <memory>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <cmath>

namespace sc2 {

struct Shape {
    std::vector<size_t> dims;
    
    Shape() {}
    explicit Shape(const std::vector<size_t>& d) : dims(d) {}
    
    size_t size() const {
        size_t s = 1;
        for (auto d : dims) s *= d;
        return s;
    }
    
    size_t ndim() const { return dims.size(); }
};

template<typename T>
class Tensor {
public:
    Tensor() : shape_(), data_(nullptr), owns_data_(false) {}
    
    explicit Tensor(const Shape& shape) : shape_(shape), owns_data_(true) {
        data_ = (T*)malloc(shape_.size() * sizeof(T));
        std::memset(data_, 0, shape_.size() * sizeof(T));
    }
    
    Tensor(const Shape& shape, T* data, bool owns = false) 
        : shape_(shape), data_(data), owns_data_(owns) {}
    
    Tensor(const Tensor& other) : shape_(other.shape_), owns_data_(true) {
        data_ = (T*)malloc(shape_.size() * sizeof(T));
        std::memcpy(data_, other.data_, shape_.size() * sizeof(T));
    }
    
    Tensor(Tensor&& other) noexcept 
        : shape_(std::move(other.shape_)), data_(other.data_), owns_data_(other.owns_data_) {
        other.data_ = nullptr;
        other.owns_data_ = false;
    }
    
    ~Tensor() {
        if (owns_data_ && data_) {
            free(data_);
        }
    }
    
    Tensor& operator=(const Tensor& other) {
        if (this != &other) {
            if (owns_data_ && data_) free(data_);
            shape_ = other.shape_;
            data_ = (T*)malloc(shape_.size() * sizeof(T));
            std::memcpy(data_, other.data_, shape_.size() * sizeof(T));
            owns_data_ = true;
        }
        return *this;
    }
    
    T& operator[](size_t i) { return data_[i]; }
    const T& operator[](size_t i) const { return data_[i]; }
    
    T* data() { return data_; }
    const T* data() const { return data_; }
    
    const Shape& shape() const { return shape_; }
    size_t size() const { return shape_.size(); }
    
    void fill(T value) {
        std::fill(data_, data_ + size(), value);
    }
    
    T sum() const {
        T s = 0;
        for (size_t i = 0; i < size(); ++i) s += data_[i];
        return s;
    }
    
    T mean() const {
        return size() > 0 ? sum() / static_cast<T>(size()) : 0;
    }
    
    size_t flatten_index(const std::vector<size_t>& indices) const {
        size_t idx = 0;
        size_t stride = 1;
        for (int i = shape_.ndim() - 1; i >= 0; --i) {
            idx += indices[i] * stride;
            stride *= shape_.dims[i];
        }
        return idx;
    }
    
    T& at(const std::vector<size_t>& indices) {
        return data_[flatten_index(indices)];
    }
    
    const T& at(const std::vector<size_t>& indices) const {
        return data_[flatten_index(indices)];
    }

private:
    Shape shape_;
    T* data_;
    bool owns_data_;
};

class GPUContext {
public:
    static GPUContext& instance() {
        static GPUContext ctx;
        return ctx;
    }
    
    bool is_available() const { return available_; }
    
    template<typename T>
    void memcpy_h2d(T* dst, const T* src, size_t count) {
        if (available_) {
            cudaMemcpy(dst, src, count * sizeof(T), cudaMemcpyHostToDevice);
        } else {
            std::memcpy(dst, src, count * sizeof(T));
        }
    }
    
    template<typename T>
    void memcpy_d2h(T* dst, const T* src, size_t count) {
        if (available_) {
            cudaMemcpy(dst, src, count * sizeof(T), cudaMemcpyDeviceToHost);
        } else {
            std::memcpy(dst, src, count * sizeof(T));
        }
    }

private:
    GPUContext() : available_(false) {}
    bool available_;
};

template<typename T>
__global__ void relu_kernel(T* output, const T* input, size_t n) {
    size_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        output[idx] = input[idx] > 0 ? input[idx] : 0;
    }
}

template<typename T>
void relu_gpu(Tensor<T>& output, const Tensor<T>& input) {
    output = Tensor<T>(input.shape());
    size_t n = input.size();
    size_t block = 256;
    size_t grid = (n + block - 1) / block;
    relu_kernel<<<grid, block>>>(output.data(), input.data(), n);
}

template<typename T>
void relu_cpu(Tensor<T>& output, const Tensor<T>& input) {
    output = Tensor<T>(input.shape());
    size_t n = input.size();
    for (size_t i = 0; i < n; ++i) {
        output[i] = input[i] > 0 ? input[i] : 0;
    }
}

template<typename T>
__global__ void matmul_kernel(const T* a, const T* b, T* c, 
                               size_t m, size_t n, size_t k) {
    size_t row = blockIdx.y * blockDim.y + threadIdx.y;
    size_t col = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (row < m && col < n) {
        T sum = 0;
        for (size_t i = 0; i < k; ++i) {
            sum += a[row * k + i] * b[i * n + col];
        }
        c[row * n + col] = sum;
    }
}

template<typename T>
Tensor<T> matmul(const Tensor<T>& a, const Tensor<T>& b, bool use_gpu = false) {
    Shape result_shape = {a.shape().dims[0], b.shape().dims[1]};
    Tensor<T> result(result_shape);
    
    if (use_gpu && GPUContext::instance().is_available()) {
        size_t m = a.shape().dims[0], k = a.shape().dims[1], n = b.shape().dims[1];
        dim3 block(16, 16);
        dim3 grid((n + 15) / 16, (m + 15) / 16);
        matmul_kernel<<<grid, block>>>(a.data(), b.data(), result.data(), m, n, k);
    } else {
        size_t m = a.shape().dims[0], k = a.shape().dims[1], n = b.shape().dims[1];
        for (size_t i = 0; i < m; ++i) {
            for (size_t j = 0; j < n; ++j) {
                T sum = 0;
                for (size_t l = 0; l < k; ++l) {
                    sum += a[{i, l}] * b[{l, j}];
                }
                result[{i, j}] = sum;
            }
        }
    }
    return result;
}

template<typename T>
__global__ void softmax_kernel(T* output, const T* input, size_t n) {
    extern __shared__ T sdata[];
    size_t tid = threadIdx.x;
    size_t idx = blockIdx.x * blockDim.x + tid;
    
    if (idx >= n) return;
    
    T x = input[idx];
    T max_val = -INFINITY;
    for (size_t i = 0; i < n; ++i) {
        max_val = fmax(max_val, input[i]);
    }
    
    T sum_exp = 0;
    for (size_t i = 0; i < n; ++i) {
        sum_exp += expf(input[i] - max_val);
    }
    
    output[idx] = expf(x - max_val) / sum_exp;
}

template<typename T>
void softmax(Tensor<T>& output, const Tensor<T>& input, bool use_gpu = false) {
    output = Tensor<T>(input.shape());
    size_t n = input.size();
    
    if (use_gpu && GPUContext::instance().is_available()) {
        size_t block = 256;
        size_t grid = (n + block - 1) / block;
        softmax_kernel<<<grid, block>>>(output.data(), input.data(), n);
    } else {
        T max_val = -INFINITY;
        for (size_t i = 0; i < n; ++i) {
            max_val = fmax(max_val, input[i]);
        }
        
        T sum_exp = 0;
        for (size_t i = 0; i < n; ++i) {
            sum_exp += std::exp(input[i] - max_val);
        }
        
        for (size_t i = 0; i < n; ++i) {
            output[i] = std::exp(input[i] - max_val) / sum_exp;
        }
    }
}

template<typename T>
class TensorOperations {
public:
    static Tensor<T> conv2d(const Tensor<T>& input, const Tensor<T>& kernel,
                            size_t stride = 1, size_t padding = 0) {
        size_t batch = input.shape().dims[0];
        size_t in_h = input.shape().dims[1];
        size_t in_w = input.shape().dims[2];
        size_t out_h = (in_h + 2 * padding - kernel.shape().dims[1]) / stride + 1;
        size_t out_w = (in_w + 2 * padding - kernel.shape().dims[2]) / stride + 1;
        
        Shape out_shape = {batch, out_h, out_w, kernel.shape().dims[0]};
        Tensor<T> output(out_shape);
        output.fill(0);
        
        return output;
    }
    
    static Tensor<T> batch_norm(const Tensor<T>& input, 
                                const Tensor<T>& gamma,
                                const Tensor<T>& beta,
                                T epsilon = 1e-5) {
        Tensor<T> output(input.shape());
        T mean = input.mean();
        T var = 0;
        
        for (size_t i = 0; i < input.size(); ++i) {
            T diff = input[i] - mean;
            var += diff * diff;
        }
        var /= input.size();
        
        for (size_t i = 0; i < input.size(); ++i) {
            output[i] = gamma[i % gamma.size()] * (input[i] - mean) / std::sqrt(var + epsilon) 
                       + beta[i % beta.size()];
        }
        
        return output;
    }
    
    static Tensor<T> attention(const Tensor<T>& q, const Tensor<T>& k, const Tensor<T>& v, bool use_gpu = false) {
        size_t seq_len = q.shape().dims[1];
        size_t d_k = q.shape().dims[2];
        
        Tensor<T> scores({q.shape().dims[0], seq_len, seq_len});
        
        for (size_t b = 0; b < q.shape().dims[0]; ++b) {
            for (size_t i = 0; i < seq_len; ++i) {
                for (size_t j = 0; j < seq_len; ++j) {
                    T s = 0;
                    for (size_t d = 0; d < d_k; ++d) {
                        s += q[{b, i, d}] * k[{b, j, d}];
                    }
                    scores[{b, i, j}] = s / std::sqrt(d_k);
                }
            }
        }
        
        Tensor<T> attn_weights;
        softmax(attn_weights, scores, use_gpu);
        
        Tensor<T> output({q.shape().dims[0], seq_len, d_k});
        for (size_t b = 0; b < q.shape().dims[0]; ++b) {
            for (size_t i = 0; i < seq_len; ++i) {
                for (size_t d = 0; d < d_k; ++d) {
                    T s = 0;
                    for (size_t j = 0; j < seq_len; ++j) {
                        s += attn_weights[{b, i, j}] * v[{b, j, d}];
                    }
                    output[{b, i, d}] = s;
                }
            }
        }
        
        return output;
    }
};

}

#endif
