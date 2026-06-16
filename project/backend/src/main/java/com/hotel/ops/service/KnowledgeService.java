package com.hotel.ops.service;

import com.hotel.ops.model.KnowledgeDoc;
import java.util.List;

public interface KnowledgeService {

  KnowledgeDoc addDoc(String title, String content);

  KnowledgeDoc updateDoc(long id, String title, String content);

  boolean deleteDoc(long id);

  List<KnowledgeDoc> listDocs();

  List<KnowledgeDoc> search(String query, int topK);
}
